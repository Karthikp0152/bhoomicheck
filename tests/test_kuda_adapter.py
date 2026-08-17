"""Tests for the provisional KudaMasterPlanAdapter.

The lookup source (1acre.in) and its URLs are confirmed real (see module
docstring in adapters/kuda.py), but parse() still has no real screenshot
to learn its shape from. These tests check that instructions() points at
the real workflow and that parse() admits its own limitation plainly
instead of guessing.
"""

from pathlib import Path

import pytest

from bhoomicheck.adapters.kuda import KudaMasterPlanAdapter
from bhoomicheck.schemas.parcel import ParcelIdentifier

PARCEL = ParcelIdentifier(
    survey_no="123/A", village="Hasanparthy", mandal="Hasanparthy", district="Warangal"
)


def test_instructions_reference_the_parcel_and_the_real_url() -> None:
    text = KudaMasterPlanAdapter().instructions(PARCEL)
    assert "123/A" in text
    assert "Hasanparthy" in text
    assert "https://1acre.in/map-layers/telangana/warangal-masterplan" in text


def test_parse_refuses_without_a_real_sample(tmp_path: Path) -> None:
    upload = tmp_path / "screenshot.png"
    upload.write_bytes(b"\x89PNG fake")
    with pytest.raises(NotImplementedError):
        KudaMasterPlanAdapter().parse(upload)
