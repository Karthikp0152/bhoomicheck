"""Tests for the Orchestrator's LangGraph wiring.

No live model calls (same convention as test_document_analysis_agent.py):
a FakeProvider satisfies LLMProvider with a scripted response, so this
test pins down that the graph actually runs all four specialist nodes
and feeds their reports into risk_report -- not what any one agent does
internally, which is already covered by that agent's own tests.
"""

import json
from pathlib import Path

from bhoomicheck.agents.document_analysis import DocumentAnalysisAgent
from bhoomicheck.orchestrator.graph import Orchestrator
from bhoomicheck.schemas.land_records import LandRecordExtract
from bhoomicheck.schemas.litigation import LitigationSearchResult
from bhoomicheck.schemas.parcel import ParcelIdentifier
from bhoomicheck.schemas.risk_report import RiskReport
from bhoomicheck.schemas.zoning import KudaMasterPlanExtract

PARCEL = ParcelIdentifier(
    survey_no="123/A", village="Hasanparthy", mandal="Hasanparthy", district="Warangal"
)

VALID_DOCUMENT_PAYLOAD = json.dumps(
    {
        "documents": [
            {
                "source_document": "sale_deed_2015_1234.pdf",
                "doc_type": "sale_deed",
                "reference_no": "1234/2015",
                "execution_date": "2015-03-12",
                "executants": ["K. Rajaiah"],
                "claimants": ["B. Swapna"],
                "extraction_confidence": {"level": "medium", "reason": "scanned copy"},
            }
        ],
        "findings": [
            {
                "check_id": "document.deed_present",
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


class FakeProvider:
    """Scripted LLMProvider, same pattern as test_document_analysis_agent.py."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    def generate(self, prompt: str, pdf_paths: list[Path]) -> str:
        self.prompts.append(prompt)
        return self.responses[len(self.prompts) - 1]


def _run(orchestrator: Orchestrator, *, road_widening: bool, prohibited: bool) -> RiskReport:
    return orchestrator.run(
        parcel=PARCEL,
        pdf_paths=[Path("sale_deed_2015_1234.pdf")],
        zoning_inputs=[
            (Path("kuda.png"), KudaMasterPlanExtract(road_widening_affects_parcel=road_widening))
        ],
        litigation_inputs=[
            (Path("ecourts.png"), LitigationSearchResult(searched_name="K. Rajaiah", cases=[]))
        ],
        land_records_inputs=[
            (Path("bhubharati.png"), LandRecordExtract(prohibited_status=prohibited))
        ],
    )


def test_run_produces_a_risk_report_from_all_four_specialists() -> None:
    document_agent = DocumentAnalysisAgent(FakeProvider([VALID_DOCUMENT_PAYLOAD]))
    orchestrator = Orchestrator(document_agent=document_agent)

    report = _run(orchestrator, road_widening=False, prohibited=False)

    assert isinstance(report, RiskReport)
    assert report.parcel == PARCEL
    assert len(report.specialist_reports) == 4
    agent_names = {r.agent_name for r in report.specialist_reports}
    assert agent_names == {"document_analysis", "zoning", "litigation", "land_records"}


def test_run_score_reflects_an_issue_from_one_specialist() -> None:
    document_agent = DocumentAnalysisAgent(FakeProvider([VALID_DOCUMENT_PAYLOAD]))
    orchestrator = Orchestrator(document_agent=document_agent)

    report = _run(orchestrator, road_widening=True, prohibited=False)

    assert report.overall_score < 100


def test_run_score_reflects_issues_from_two_specialists() -> None:
    # A fresh Orchestrator (and FakeProvider) per run: the fake only has
    # one scripted response queued, and each full graph run calls it once.
    both_issues = _run(
        Orchestrator(document_agent=DocumentAnalysisAgent(FakeProvider([VALID_DOCUMENT_PAYLOAD]))),
        road_widening=True,
        prohibited=True,
    )
    one_issue = _run(
        Orchestrator(document_agent=DocumentAnalysisAgent(FakeProvider([VALID_DOCUMENT_PAYLOAD]))),
        road_widening=True,
        prohibited=False,
    )

    assert both_issues.overall_score < one_issue.overall_score
