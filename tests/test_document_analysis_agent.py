"""Tests for the Document Analysis Agent's validation-retry loop.

No live model calls (per testing conventions): a FakeProvider satisfies
the LLMProvider Protocol with scripted responses, letting us pin down the
retry behaviour — the core of architecture principle 1 — deterministically.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from bhoomicheck.agents.document_analysis import DocumentAnalysisAgent
from bhoomicheck.schemas.document import DocumentAnalysisReport
from bhoomicheck.schemas.parcel import ParcelIdentifier

PARCEL = ParcelIdentifier(
    survey_no="123/A", village="Hasanparthy", mandal="Hasanparthy", district="Warangal"
)

VALID_PAYLOAD = json.dumps(
    {
        "documents": [
            {
                "source_document": "sale_deed_2015_1234.pdf",
                "doc_type": "sale_deed",
                "reference_no": "1234/2015",
                "execution_date": "2015-03-12",
                "executants": ["K. Rajaiah"],
                "claimants": ["B. Swapna"],
                "extraction_confidence": {
                    "level": "medium",
                    "reason": "scanned copy, stamp obscures endorsement",
                },
            }
        ],
        "findings": [
            {
                "claim": "sale deed 1234/2015 names B. Swapna as claimant",
                "status": "verified_ok",
                "provenance": {
                    "source_name": "uploaded sale deed",
                    "source_type": "manual",
                    "document": "sale_deed_2015_1234.pdf",
                    "fetched_at": "2026-07-19",
                },
                "confidence": {"level": "high", "reason": "clearly printed party names"},
            }
        ],
    }
)

# Structurally valid JSON, but the payload violates a schema rule
# (confidence.reason must be non-empty), so validation must fail.
INVALID_PAYLOAD = VALID_PAYLOAD.replace("clearly printed party names", "")


class FakeProvider:
    """Scripted LLMProvider: returns queued responses, records prompts."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    def generate(self, prompt: str, pdf_paths: list[Path]) -> str:
        self.prompts.append(prompt)
        return self.responses[len(self.prompts) - 1]


def test_valid_first_response_produces_report() -> None:
    agent = DocumentAnalysisAgent(FakeProvider([VALID_PAYLOAD]))
    report = agent.analyze(PARCEL, [Path("sale_deed_2015_1234.pdf")])
    assert isinstance(report, DocumentAnalysisReport)
    assert report.parcel == PARCEL  # system-supplied, not model-supplied
    assert report.agent_name == "document_analysis"
    assert len(report.documents) == 1


def test_invalid_response_is_retried_with_error_feedback() -> None:
    provider = FakeProvider([INVALID_PAYLOAD, VALID_PAYLOAD])
    agent = DocumentAnalysisAgent(provider)
    report = agent.analyze(PARCEL, [])
    assert len(provider.prompts) == 2
    # The retry prompt must carry the validation error so the model can
    # fix the specific field rather than guess.
    assert "at least 1 character" in provider.prompts[1]
    assert len(report.findings) == 1


def test_raises_after_retries_exhausted() -> None:
    provider = FakeProvider([INVALID_PAYLOAD] * 3)
    agent = DocumentAnalysisAgent(provider, max_retries=2)
    with pytest.raises(ValidationError):
        agent.analyze(PARCEL, [])
    assert len(provider.prompts) == 3  # initial + 2 retries, then loud failure
