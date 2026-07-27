"""Document Analysis Agent: uploaded land documents -> DocumentAnalysisReport.

Works offline on uploaded PDFs, no portal dependency (Phase 1). The LLM
extracts per-document structure and cross-document findings; this module
owns validation, the retry loop, and assembly of the final report.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ValidationError

from bhoomicheck.agents.provider import LLMProvider
from bhoomicheck.schemas.confidence import Confidence
from bhoomicheck.schemas.document import DocumentAnalysisReport, ExtractedDocument
from bhoomicheck.schemas.finding import Finding
from bhoomicheck.schemas.parcel import ParcelIdentifier
from bhoomicheck.schemas.provenance import Provenance


class _LLMPayload(BaseModel):
    """The slice of the report the model is asked to produce.

    Deliberately not the whole DocumentAnalysisReport: parcel identity and
    the timestamp are facts the system already knows, and asking a model
    to echo known facts is asking it to hallucinate them.
    """

    documents: list[ExtractedDocument]
    findings: list[Finding]


PROMPT_TEMPLATE = """\
You are a land-records document analyst for parcels in Telangana, India.
Read the attached document(s) for the parcel below and respond with JSON
only — no prose, no markdown fences.

Parcel: survey no. {survey_no}, village {village}, mandal {mandal}, \
district {district}.
Today's date: {today}. The attached files, in order, are: {filenames}.

Your JSON must match this schema exactly:
{schema}

Rules:
- One entry in "documents" per attached file; source_document must be the
  exact filename from the list above (never invent a filename).
- Every finding needs provenance (source_type "manual", document = the
  filename it came from, fetched_at = today's date given above) and a
  confidence with a concrete reason.
- If something cannot be read or verified, report it as a finding with
  status "not_verified" — never omit it silently.
- Set each finding's category to the closest risk family in the schema;
  use "other" only when nothing else fits.
- Only use category "layout_approval" when the document itself shows
  evidence of a subdivided layout/venture (plot numbers, the word
  "layout", an LP/venture number, HMDA/DTCP references). Undivided
  agricultural or single-survey-number land with no such evidence should
  not get a layout_approval finding at all.
- Express extraction uncertainty honestly in extraction_confidence.
"""

RETRY_TEMPLATE = """\
Your previous response failed validation with these errors:
{errors}

Produce corrected JSON matching the schema. Respond with JSON only.
"""


def _cross_check_survey_numbers(
    parcel: ParcelIdentifier, documents: list[ExtractedDocument], today: str
) -> list[Finding]:
    """Flag any document whose stated survey number disagrees with the parcel's.

    Done here in plain code, not left to the model: whether two survey
    numbers match is a mechanical fact, not a judgment call (the same
    reasoning that keeps scoring rules in rules.yaml instead of a prompt —
    principle 5). Doing it in code also means the check can never be
    quietly skipped by the model on a given run.
    """
    findings: list[Finding] = []
    for doc in documents:
        if doc.survey_number is None:
            continue
        if doc.survey_number.strip() == parcel.survey_no.strip():
            continue
        findings.append(
            Finding(
                claim=(
                    f"{doc.source_document} states survey no. "
                    f"{doc.survey_number!r}, which does not match the "
                    f"parcel's survey no. {parcel.survey_no!r}"
                ),
                category="deed_chain",
                status="issue_found",
                provenance=Provenance(
                    source_name="survey number cross-check",
                    source_type="manual",
                    document=doc.source_document,
                    fetched_at=today,
                ),
                confidence=Confidence(
                    level="high",
                    reason="exact string comparison against the parcel identifier",
                ),
            )
        )
    return findings


class DocumentAnalysisAgent:
    """Runs document analysis for one parcel over its uploaded PDFs."""

    def __init__(self, provider: LLMProvider, max_retries: int = 2) -> None:
        """
        Args:
            provider: The model backend to call.
            max_retries: How many *additional* attempts after the first,
                each fed the previous validation errors. Small on purpose:
                if the model can't fix its output in two corrections, more
                tries usually just burn tokens.
        """
        self.provider = provider
        self.max_retries = max_retries

    def analyze(
        self, parcel: ParcelIdentifier, pdf_paths: list[Path]
    ) -> DocumentAnalysisReport:
        """Analyze the uploaded documents and return a validated report.

        Raises:
            ValidationError: If the model still produces invalid output
                after all retries — surfaced loudly, never papered over.
        """
        # Captured once and reused below: the cross-check finding's own
        # provenance must cite the same date the model was told, not a
        # second, possibly-later call to now().
        today = datetime.now(timezone.utc).date().isoformat()
        prompt = PROMPT_TEMPLATE.format(
            survey_no=parcel.survey_no,
            village=parcel.village,
            mandal=parcel.mandal,
            district=parcel.district,
            # Facts the system knows go into the prompt, never guessed by
            # the model: real filenames and the actual date (provenance
            # principle — a hallucinated filename is untraceable).
            today=today,
            filenames=", ".join(p.name for p in pdf_paths),
            schema=json.dumps(_LLMPayload.model_json_schema(), indent=2),
        )

        for attempt in range(self.max_retries + 1):
            raw = self.provider.generate(prompt, pdf_paths)
            try:
                payload = _LLMPayload.model_validate_json(raw)
            except ValidationError as e:
                if attempt == self.max_retries:
                    raise
                # Feed the exact validation errors back so the model can
                # fix the specific fields, not guess at what went wrong.
                prompt = prompt + "\n\n" + RETRY_TEMPLATE.format(errors=e)
                continue
            findings = payload.findings + _cross_check_survey_numbers(
                parcel, payload.documents, today
            )
            return DocumentAnalysisReport(
                parcel=parcel,
                generated_at=datetime.now(timezone.utc),
                documents=payload.documents,
                findings=findings,
            )

        raise AssertionError("unreachable")  # loop always returns or raises
