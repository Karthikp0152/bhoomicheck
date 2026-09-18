"""Tests for the Growth Potential Agent's deterministic Finding-building logic.

Same style as test_zoning_agent.py, but pins down the one real difference:
these findings are informational/upside, so they only ever resolve to
verified_ok or not_verified -- never issue_found, since there's nothing
wrong with a parcel simply having lower growth potential.
"""

from pathlib import Path

from bhoomicheck.agents.growth_potential import GrowthPotentialAgent
from bhoomicheck.schemas.parcel import ParcelIdentifier
from bhoomicheck.schemas.zoning import KudaMasterPlanExtract

PARCEL = ParcelIdentifier(
    survey_no="123/A", village="Hasanparthy", mandal="Hasanparthy", district="Warangal"
)


def test_fully_populated_extract_produces_three_findings() -> None:
    extract = KudaMasterPlanExtract(
        in_growth_corridor=True,
        near_major_road_upgrade=True,
        near_approved_layout=False,
    )
    report = GrowthPotentialAgent().report(PARCEL, [(Path("kuda.png"), extract)])

    assert report.agent_name == "growth_potential"
    assert len(report.findings) == 3
    assert len(report.extracts) == 1


def test_no_finding_is_ever_issue_found() -> None:
    extract = KudaMasterPlanExtract(
        in_growth_corridor=False,
        near_major_road_upgrade=False,
        near_approved_layout=False,
    )
    report = GrowthPotentialAgent().report(PARCEL, [(Path("kuda.png"), extract)])

    assert all(f.status != "issue_found" for f in report.findings)


def test_growth_corridor_true_is_verified_ok_with_positive_claim() -> None:
    extract = KudaMasterPlanExtract(in_growth_corridor=True)
    report = GrowthPotentialAgent().report(PARCEL, [(Path("kuda.png"), extract)])
    finding = next(f for f in report.findings if f.check_id == "growth_potential.growth_corridor")
    assert finding.status == "verified_ok"
    assert "falls within" in finding.claim


def test_growth_corridor_false_is_still_verified_ok() -> None:
    extract = KudaMasterPlanExtract(in_growth_corridor=False)
    report = GrowthPotentialAgent().report(PARCEL, [(Path("kuda.png"), extract)])
    finding = next(f for f in report.findings if f.check_id == "growth_potential.growth_corridor")
    assert finding.status == "verified_ok"
    assert "does not fall within" in finding.claim


def test_missing_field_is_not_verified() -> None:
    extract = KudaMasterPlanExtract()  # nothing legible
    report = GrowthPotentialAgent().report(PARCEL, [(Path("kuda.png"), extract)])
    assert all(f.status == "not_verified" for f in report.findings)


def test_provenance_document_matches_uploaded_filename() -> None:
    extract = KudaMasterPlanExtract(in_growth_corridor=True)
    report = GrowthPotentialAgent().report(PARCEL, [(Path("my_screenshot.png"), extract)])
    for finding in report.findings:
        assert finding.provenance is not None
        assert finding.provenance.document == "my_screenshot.png"
