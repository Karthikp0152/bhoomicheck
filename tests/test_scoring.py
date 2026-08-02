"""Tests for the scoring engine and the shipped rules.yaml.

The real rules file is itself under test: loading it exercises the same
validation any edited version must pass, so a broken rules.yaml fails CI
before it can mis-score a parcel.
"""

import pytest
from pydantic import ValidationError

from bhoomicheck.scoring.engine import RuleSet, evaluate, load_rules
from bhoomicheck.schemas.finding import Finding

from tests.test_schemas import make_confidence, make_finding


def flagged(category: str, status: str) -> Finding:
    """A finding that should be flagged by the engine."""
    provenance = None if status == "not_verified" else "keep"
    if provenance is None:
        return make_finding(category=category, status=status, provenance=None)
    return make_finding(category=category, status=status)


class TestRulesFile:
    def test_shipped_rules_load_and_validate(self) -> None:
        ruleset = load_rules()
        assert ruleset.version == 1
        assert ruleset.rules  # non-empty
        assert set(ruleset.defaults) == {"issue_found", "not_verified"}

    def test_duplicate_rules_rejected(self) -> None:
        rule = {
            "category": "mortgage",
            "status": "issue_found",
            "severity": "high",
            "rationale": "x",
        }
        with pytest.raises(ValidationError, match="duplicate rule"):
            RuleSet.model_validate(
                {"version": 1, "defaults": {"issue_found": "high", "not_verified": "medium"}, "rules": [rule, rule]}
            )


class TestEvaluate:
    @pytest.fixture()
    def ruleset(self) -> RuleSet:
        return load_rules()

    def test_all_verified_ok_is_clear(self, ruleset: RuleSet) -> None:
        findings = [make_finding(), make_finding(category="ownership")]
        assessment = evaluate(findings, ruleset)
        assert assessment.overall == "clear"
        assert assessment.flags == []

    def test_specific_rule_sets_severity_and_rationale(self, ruleset: RuleSet) -> None:
        assessment = evaluate([flagged("prohibited_land", "issue_found")], ruleset)
        assert assessment.overall == "critical"
        assert "cannot be legally transferred" in assessment.flags[0].rationale

    def test_unsanctioned_layout_is_critical(self, ruleset: RuleSet) -> None:
        # An unapproved layout blocks building permission/utilities even
        # with an otherwise clean title — same severity class as
        # master_plan_road and ftl_buffer, not a generic "other" default.
        assessment = evaluate([flagged("layout_approval", "issue_found")], ruleset)
        assert assessment.overall == "critical"
        assert "building permission" in assessment.flags[0].rationale

    def test_default_applies_when_no_specific_rule(self, ruleset: RuleSet) -> None:
        # (mortgage, not_verified) deliberately has no specific rule in
        # rules.yaml, so the not_verified default (medium) must apply.
        assert ruleset.find("mortgage", "not_verified") is None
        assessment = evaluate([flagged("mortgage", "not_verified")], ruleset)
        assert assessment.overall == "medium"
        assert "default severity" in assessment.flags[0].rationale

    def test_worst_severity_wins_and_flags_sorted(self, ruleset: RuleSet) -> None:
        findings = [
            flagged("mortgage", "not_verified"),      # medium (default)
            flagged("ftl_buffer", "issue_found"),     # critical
            flagged("deed_chain", "issue_found"),     # high
        ]
        assessment = evaluate(findings, ruleset)
        assert assessment.overall == "critical"
        assert [f.severity for f in assessment.flags] == ["critical", "high", "medium"]

    def test_not_verified_never_scores_clear(self, ruleset: RuleSet) -> None:
        # Principle 6 as an executable guarantee, for every category.
        categories = [
            "ownership", "deed_chain", "mortgage", "litigation",
            "prohibited_land", "master_plan_road", "ftl_buffer",
            "layout_approval", "other",
        ]
        for category in categories:
            assessment = evaluate([flagged(category, "not_verified")], ruleset)
            assert assessment.overall != "clear", category
