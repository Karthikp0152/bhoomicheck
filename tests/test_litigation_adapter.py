"""Tests for the provisional LitigationAdapter.

Pin down two things: instructions() points at the real, confirmed eCourts
URLs and covers every name variant given, and parse() admits it has no
real sample to learn from yet rather than guessing. Also locks in the
hard-guardrail behaviour that a case extract can't silently claim to be a
confirmed identity match.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from bhoomicheck.adapters.litigation import (
    LitigationAdapter,
    LitigationCaseExtract,
    LitigationSearchQuery,
)

QUERY = LitigationSearchQuery(full_name="K. Rajaiah", also_known_as=["Rajaiah Kondapaka"])


def test_instructions_cover_both_courts_and_every_name_variant() -> None:
    text = LitigationAdapter().instructions(QUERY)
    assert "K. Rajaiah" in text
    assert "Rajaiah Kondapaka" in text
    assert "warangal.dcourts.gov.in" in text
    assert "hcservices.ecourts.gov.in" in text


def test_parse_refuses_without_a_real_sample(tmp_path: Path) -> None:
    upload = tmp_path / "search_result.png"
    upload.write_bytes(b"\x89PNG fake")
    with pytest.raises(NotImplementedError):
        LitigationAdapter().parse(upload)


def test_case_extract_match_basis_cannot_be_overridden() -> None:
    # match_basis is pinned to "name_search_unconfirmed" -- asserting the
    # opposite value must fail validation, not silently be accepted.
    with pytest.raises(ValidationError):
        LitigationCaseExtract(
            court="District Court, Warangal",
            status="pending",
            matched_party_name="K. Rajaiah",
            match_basis="confirmed",  # type: ignore[arg-type]
        )


def test_case_extract_defaults_to_unconfirmed_match_basis() -> None:
    case = LitigationCaseExtract(
        court="District Court, Warangal",
        status="pending",
        matched_party_name="K. Rajaiah",
    )
    assert case.match_basis == "name_search_unconfirmed"
