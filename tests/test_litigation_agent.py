"""Tests for the Litigation Agent's deterministic Finding-building logic.

No fake provider needed here (unlike DocumentAnalysisAgent's tests) --
this agent takes already-structured LitigationSearchResult objects and
maps them to Findings with plain code, so the tests just check that
mapping directly.
"""

from pathlib import Path

from bhoomicheck.agents.litigation import LitigationAgent
from bhoomicheck.schemas.litigation import LitigationCaseExtract, LitigationSearchResult
from bhoomicheck.schemas.parcel import ParcelIdentifier

PARCEL = ParcelIdentifier(
    survey_no="123/A", village="Hasanparthy", mandal="Hasanparthy", district="Warangal"
)


def test_no_cases_found_produces_verified_ok_with_caveat() -> None:
    result = LitigationSearchResult(searched_name="K. Rajaiah", cases=[])
    report = LitigationAgent().report(PARCEL, [(Path("k_rajaiah.png"), result)])

    assert report.agent_name == "litigation"
    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.status == "verified_ok"
    assert finding.provenance is not None
    assert finding.provenance.document == "k_rajaiah.png"
    # Absence of a match must stay honestly caveated, not read as a clean bill.
    assert "misspellings" in finding.confidence.reason


def test_cases_found_produce_issue_found_with_low_confidence() -> None:
    case = LitigationCaseExtract(
        court="District Court, Warangal",
        case_no="OS/45/2019",
        status="pending",
        matched_party_name="K. Rajaiah",
    )
    result = LitigationSearchResult(searched_name="K. Rajaiah", cases=[case])
    report = LitigationAgent().report(PARCEL, [(Path("k_rajaiah.png"), result)])

    finding = report.findings[0]
    assert finding.status == "issue_found"
    assert "OS/45/2019" in finding.claim
    # A name match alone must never be reported as a confirmed verdict.
    assert finding.confidence.level == "low"
    assert "not confirmed" in finding.confidence.reason


def test_multiple_name_variants_each_produce_their_own_finding() -> None:
    result_a = LitigationSearchResult(searched_name="K. Rajaiah", cases=[])
    result_b = LitigationSearchResult(searched_name="Rajaiah Kondapaka", cases=[])
    report = LitigationAgent().report(
        PARCEL,
        [
            (Path("variant_a.png"), result_a),
            (Path("variant_b.png"), result_b),
        ],
    )

    assert len(report.findings) == 2
    assert len(report.searches) == 2
