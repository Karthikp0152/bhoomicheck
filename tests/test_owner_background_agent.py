"""Tests for the Owner Background Agent's deterministic Finding-building logic.

Same style as test_zoning_agent.py/test_land_records_agent.py: no fake
provider needed, plain-code mapping from structured extracts to Findings.
"""

from pathlib import Path

from bhoomicheck.agents.owner_background import OwnerBackgroundAgent
from bhoomicheck.schemas.owner_background import OwnerBackgroundExtract
from bhoomicheck.schemas.parcel import ParcelIdentifier

PARCEL = ParcelIdentifier(
    survey_no="123/A", village="Hasanparthy", mandal="Hasanparthy", district="Warangal"
)


def test_direct_sale_produces_two_findings_no_poa_registered_finding() -> None:
    extract = OwnerBackgroundExtract(is_poa_sale=False, seller_name_matches_title=True)
    report = OwnerBackgroundAgent().report(PARCEL, [(Path("igrs.png"), extract)])

    assert report.agent_name == "owner_background"
    assert len(report.findings) == 2
    check_ids = {f.check_id for f in report.findings}
    assert check_ids == {"owner_background.poa_sale", "owner_background.seller_identity"}


def test_poa_sale_produces_three_findings_including_poa_registered() -> None:
    extract = OwnerBackgroundExtract(
        is_poa_sale=True, poa_registered=True, seller_name_matches_title=True
    )
    report = OwnerBackgroundAgent().report(PARCEL, [(Path("igrs.png"), extract)])

    check_ids = {f.check_id for f in report.findings}
    assert check_ids == {
        "owner_background.poa_sale",
        "owner_background.poa_registered",
        "owner_background.seller_identity",
    }


def test_poa_sale_is_issue_found() -> None:
    extract = OwnerBackgroundExtract(is_poa_sale=True)
    report = OwnerBackgroundAgent().report(PARCEL, [(Path("igrs.png"), extract)])
    poa_finding = next(f for f in report.findings if f.check_id == "owner_background.poa_sale")
    assert poa_finding.status == "issue_found"
    assert "Suraj Lamp" in poa_finding.confidence.reason


def test_direct_sale_is_verified_ok() -> None:
    extract = OwnerBackgroundExtract(is_poa_sale=False)
    report = OwnerBackgroundAgent().report(PARCEL, [(Path("igrs.png"), extract)])
    poa_finding = next(f for f in report.findings if f.check_id == "owner_background.poa_sale")
    assert poa_finding.status == "verified_ok"


def test_unregistered_poa_is_issue_found() -> None:
    extract = OwnerBackgroundExtract(is_poa_sale=True, poa_registered=False)
    report = OwnerBackgroundAgent().report(PARCEL, [(Path("igrs.png"), extract)])
    poa_registered = next(
        f for f in report.findings if f.check_id == "owner_background.poa_registered"
    )
    assert poa_registered.status == "issue_found"


def test_seller_identity_mismatch_is_issue_found() -> None:
    extract = OwnerBackgroundExtract(is_poa_sale=False, seller_name_matches_title=False)
    report = OwnerBackgroundAgent().report(PARCEL, [(Path("igrs.png"), extract)])
    identity = next(f for f in report.findings if f.check_id == "owner_background.seller_identity")
    assert identity.status == "issue_found"


def test_missing_fields_are_not_verified_not_silently_ok() -> None:
    extract = OwnerBackgroundExtract()
    report = OwnerBackgroundAgent().report(PARCEL, [(Path("igrs.png"), extract)])
    # is_poa_sale is None -> not_verified, and since it's not True, no
    # poa_registered finding is produced at all -- only 2 findings.
    assert len(report.findings) == 2
    assert all(f.status == "not_verified" for f in report.findings)


def test_provenance_document_matches_uploaded_filename() -> None:
    extract = OwnerBackgroundExtract(is_poa_sale=False)
    report = OwnerBackgroundAgent().report(PARCEL, [(Path("my_screenshot.png"), extract)])
    for finding in report.findings:
        assert finding.provenance is not None
        assert finding.provenance.document == "my_screenshot.png"
