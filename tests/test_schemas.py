"""Tests for the core schema trio: Provenance, Confidence, Finding.

These pin down the validation rules that enforce architecture principles
3 (provenance), 4 (confidence), and 6 (fail loudly). If a refactor
loosens any of those rules, a test here should fail.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from bhoomicheck.schemas.confidence import Confidence
from bhoomicheck.schemas.finding import Finding
from bhoomicheck.schemas.provenance import Provenance


def make_provenance(**overrides: object) -> Provenance:
    """A valid baseline Provenance; tests override single fields to break it."""
    fields: dict[str, object] = {
        "source_name": "Bhu Bharati",
        "source_type": "scrape",
        "url": "https://bhubharati.telangana.gov.in/record/123A",
        "fetched_at": "2026-07-19",
    }
    fields.update(overrides)
    return Provenance(**fields)  # type: ignore[arg-type]


def make_confidence(**overrides: object) -> Confidence:
    """A valid baseline Confidence."""
    fields: dict[str, object] = {
        "level": "high",
        "reason": "exact survey number match",
    }
    fields.update(overrides)
    return Confidence(**fields)  # type: ignore[arg-type]


class TestProvenance:
    def test_valid_with_url(self) -> None:
        p = make_provenance()
        assert p.fetched_at == date(2026, 7, 19)  # string was coerced to date

    def test_valid_with_document_only(self) -> None:
        p = make_provenance(url=None, document="prohibited_lands_result.pdf")
        assert p.document is not None

    def test_rejects_missing_url_and_document(self) -> None:
        with pytest.raises(ValidationError, match="url or document"):
            make_provenance(url=None, document=None)

    def test_rejects_unknown_source_type(self) -> None:
        with pytest.raises(ValidationError):
            make_provenance(source_type="guess")

    def test_rejects_unparseable_date(self) -> None:
        with pytest.raises(ValidationError):
            make_provenance(fetched_at="yesterday")


class TestConfidence:
    def test_valid(self) -> None:
        c = make_confidence(level="medium")
        assert c.level == "medium"

    def test_rejects_empty_reason(self) -> None:
        with pytest.raises(ValidationError):
            make_confidence(reason="")

    def test_rejects_unknown_level(self) -> None:
        with pytest.raises(ValidationError):
            make_confidence(level="pretty sure")


class TestFinding:
    def test_valid_verified_ok(self) -> None:
        f = Finding(
            claim="survey no. 123/A absent from prohibited-lands register",
            status="verified_ok",
            provenance=make_provenance(),
            confidence=make_confidence(),
        )
        assert f.status == "verified_ok"

    def test_nested_dicts_are_validated(self) -> None:
        # Agents emit plain JSON; nested dicts must round-trip into models.
        f = Finding(
            claim="claim",
            status="verified_ok",
            provenance={
                "source_name": "IGRS",
                "source_type": "api",
                "url": "https://igrs.telangana.gov.in/ec/123",
                "fetched_at": "2026-07-19",
            },
            confidence={"level": "low", "reason": "partial name match only"},
        )
        assert isinstance(f.provenance, Provenance)
        assert isinstance(f.confidence, Confidence)

    def test_not_verified_may_omit_provenance(self) -> None:
        f = Finding(
            claim="litigation status of survey no. 123/A",
            status="not_verified",
            confidence=make_confidence(level="low", reason="portal unreachable"),
        )
        assert f.provenance is None

    @pytest.mark.parametrize("status", ["verified_ok", "issue_found"])
    def test_checked_statuses_require_provenance(self, status: str) -> None:
        with pytest.raises(ValidationError, match="requires provenance"):
            Finding(
                claim="claim",
                status=status,  # type: ignore[arg-type]
                confidence=make_confidence(),
            )

    def test_nested_error_reports_full_path(self) -> None:
        # The retry loop feeds validation errors back to the agent; the
        # error location must point into the nested model, not just "provenance".
        with pytest.raises(ValidationError) as exc_info:
            Finding(
                claim="claim",
                status="verified_ok",
                provenance={
                    "source_name": "Y",
                    "source_type": "api",
                    "url": "http://y",
                    "fetched_at": "not a date",
                },
                confidence=make_confidence(),
            )
        assert ("provenance", "fetched_at") == exc_info.value.errors()[0]["loc"]
