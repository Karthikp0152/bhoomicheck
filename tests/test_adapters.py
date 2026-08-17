"""Tests for the ManualAdapter base class.

No concrete government source is wired up yet, so these tests use a
minimal stand-in adapter to pin down the contract every real adapter
(KUDA master plan, Dharani, IGRS...) will have to satisfy.
"""

from pathlib import Path

import pytest

from bhoomicheck.adapters.base import ManualAdapter
from bhoomicheck.schemas.parcel import ParcelIdentifier

PARCEL = ParcelIdentifier(
    survey_no="123/A", village="Hasanparthy", mandal="Hasanparthy", district="Warangal"
)


class _StubAdapter(ManualAdapter[str]):
    source_name = "Stub Registry"

    def instructions(self, parcel: ParcelIdentifier) -> str:
        return f"Fetch the stub record for survey no. {parcel.survey_no}."

    def parse(self, upload_path: Path) -> str:
        return upload_path.read_text()


def test_instructions_reference_the_parcel() -> None:
    adapter = _StubAdapter()
    assert "123/A" in adapter.instructions(PARCEL)


def test_parse_returns_subclass_defined_shape(tmp_path: Path) -> None:
    upload = tmp_path / "record.txt"
    upload.write_text("raw content")
    adapter = _StubAdapter()
    assert adapter.parse(upload) == "raw content"


def test_cannot_instantiate_without_implementing_abstract_methods() -> None:
    class _Incomplete(ManualAdapter[str]):
        source_name = "Incomplete"

    with pytest.raises(TypeError):
        _Incomplete()  # type: ignore[abstract]
