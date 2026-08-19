"""Tests for the provisional LandRecordsAdapter.

Pin down: instructions() points at the real, confirmed Bhu Bharati URL
and references the parcel's own fields, and parse() admits it has no
real sample to learn from yet rather than guessing.
"""

from pathlib import Path

import pytest

from bhoomicheck.adapters.land_records import LandRecordsAdapter
from bhoomicheck.schemas.parcel import ParcelIdentifier

PARCEL = ParcelIdentifier(
    survey_no="123/A", village="Hasanparthy", mandal="Hasanparthy", district="Warangal"
)


def test_instructions_reference_the_parcel_and_the_real_url() -> None:
    text = LandRecordsAdapter().instructions(PARCEL)
    assert "123/A" in text
    assert "Hasanparthy" in text
    assert "Warangal" in text
    assert "https://bhubharati.telangana.gov.in/knowLandStatus" in text


def test_parse_refuses_without_a_real_sample(tmp_path: Path) -> None:
    upload = tmp_path / "screenshot.png"
    upload.write_bytes(b"\x89PNG fake")
    with pytest.raises(NotImplementedError):
        LandRecordsAdapter().parse(upload)
