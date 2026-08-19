"""Tests for the provisional OwnerBackgroundAdapter.

Pin down: instructions() points at the real, confirmed IGRS URL, adapts
based on whether a POA document number is already known, and parse()
admits it has no real sample to learn from yet rather than guessing.
"""

from pathlib import Path

import pytest

from bhoomicheck.adapters.owner_background import OwnerBackgroundAdapter
from bhoomicheck.schemas.owner_background import OwnerBackgroundQuery


def test_instructions_reference_the_seller_and_the_real_url() -> None:
    query = OwnerBackgroundQuery(seller_name="K. Rajaiah")
    text = OwnerBackgroundAdapter().instructions(query)
    assert "K. Rajaiah" in text
    assert "https://registration.telangana.gov.in/" in text
    assert "Suraj Lamp" in text


def test_instructions_include_poa_document_number_when_known() -> None:
    query = OwnerBackgroundQuery(seller_name="K. Rajaiah", poa_document_no="GPA/456/2020")
    text = OwnerBackgroundAdapter().instructions(query)
    assert "GPA/456/2020" in text


def test_parse_refuses_without_a_real_sample(tmp_path: Path) -> None:
    upload = tmp_path / "screenshot.png"
    upload.write_bytes(b"\x89PNG fake")
    with pytest.raises(NotImplementedError):
        OwnerBackgroundAdapter().parse(upload)
