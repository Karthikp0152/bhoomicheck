"""Tests for RiskScorer against the real rules.yaml.

Deliberately tests against the actual shipped rules file, not a fixture
copy -- the whole point of principle 5 is that rules.yaml is the single
source of truth, so a test that scored against a different file could
pass while the real rules were broken.
"""

from bhoomicheck.schemas.confidence import Confidence
from bhoomicheck.schemas.finding import Finding
from bhoomicheck.schemas.provenance import Provenance
from bhoomicheck.scoring.engine import RiskScorer


def make_finding(check_id: str, status: str, confidence_level: str) -> Finding:
    provenance = None
    if status != "not_verified":
        provenance = Provenance(
            source_name="test source",
            source_type="manual",
            document="test.pdf",
            fetched_at="2026-07-19",
        )
    return Finding(
        check_id=check_id,
        claim="test claim",
        status=status,  # type: ignore[arg-type]
        provenance=provenance,
        confidence=Confidence(level=confidence_level, reason="test reason"),  # type: ignore[arg-type]
    )


def test_no_findings_scores_100() -> None:
    result = RiskScorer().score([])
    assert result.score == 100
    assert result.scored_findings == []


def test_all_verified_ok_scores_100() -> None:
    findings = [
        make_finding("zoning.classification", "verified_ok", "high"),
        make_finding("litigation.name_match", "verified_ok", "medium"),
    ]
    result = RiskScorer().score(findings)
    assert result.score == 100


def test_high_confidence_setback_issue_is_the_costliest_single_finding() -> None:
    setback = make_finding("zoning.road_widening_setback", "issue_found", "high")
    litigation = make_finding("litigation.name_match", "issue_found", "high")
    classification = make_finding("zoning.classification", "issue_found", "high")

    setback_score = RiskScorer().score([setback]).score
    litigation_score = RiskScorer().score([litigation]).score
    classification_score = RiskScorer().score([classification]).score

    # The flagship risk (CLAUDE.md's problem statement) must outweigh a
    # merely-unconfirmed litigation lead or a classification note.
    assert setback_score < litigation_score < classification_score


def test_unknown_check_id_falls_through_to_default_rule() -> None:
    finding = make_finding("document.some_novel_llm_discovered_issue", "issue_found", "medium")
    result = RiskScorer().score([finding])

    scored = result.scored_findings[0]
    assert scored.rule_matched == "default"
    assert scored.points_deducted == 12  # default.issue_found.medium


def test_score_never_goes_below_zero() -> None:
    findings = [
        make_finding("zoning.road_widening_setback", "issue_found", "high"),
        make_finding("zoning.ftl_buffer", "issue_found", "high"),
        make_finding("litigation.name_match", "issue_found", "high"),
        make_finding("zoning.classification", "issue_found", "high"),
    ]
    result = RiskScorer().score(findings)
    assert result.score == 0


def test_scored_finding_records_which_rule_fired() -> None:
    finding = make_finding("zoning.ftl_buffer", "issue_found", "low")
    result = RiskScorer().score([finding])

    scored = result.scored_findings[0]
    assert scored.check_id == "zoning.ftl_buffer"
    assert scored.rule_matched == "zoning.ftl_buffer"
    assert scored.points_deducted == 12
