"""RiskScorer: turns a set of Findings into an auditable overall score.

The actual weights live in rules.yaml, not here (architecture principle
5) -- this module only loads and applies them, and records exactly which
rule fired for which finding, so a score is always explainable: "why is
this parcel at 62?" has a concrete per-finding answer, not a black box.

Known simplification: verified_ok always costs 0 points regardless of
confidence. A low-confidence "verified_ok" (e.g. "probably fine, but the
screenshot was blurry") arguably deserves its own signal -- CLAUDE.md's
own example is "low confidence on ownership -> flag for manual check".
That's a *review-flagging* concern, not a *scoring* one, and this module
doesn't attempt it yet; RiskScore.scored_findings exposes every finding's
confidence level so a future pass can add that without changing the
score's meaning.
"""

from pathlib import Path

import yaml

from bhoomicheck.schemas.finding import Finding
from bhoomicheck.schemas.scoring import RiskScore, ScoredFinding

RULES_PATH = Path(__file__).parent / "rules.yaml"


class RiskScorer:
    """Loads rules.yaml once and scores Finding lists against it."""

    def __init__(self, rules_path: Path = RULES_PATH) -> None:
        with rules_path.open() as f:
            data = yaml.safe_load(f)
        self._default: dict = data["default"]
        self._rules: dict = data["rules"]

    def score(self, findings: list[Finding]) -> RiskScore:
        """Score a set of Findings (typically one agent report's worth)."""
        scored = [self._score_one(finding) for finding in findings]
        total_deducted = sum(sf.points_deducted for sf in scored)
        return RiskScore(score=max(0, 100 - total_deducted), scored_findings=scored)

    def _score_one(self, finding: Finding) -> ScoredFinding:
        rule = self._rules.get(finding.check_id)
        rule_matched = finding.check_id if rule is not None else "default"
        rule = rule if rule is not None else self._default

        status_rule = rule[finding.status]
        # verified_ok is a flat int in rules.yaml; the other two statuses
        # are dicts keyed by confidence level (see module docstring on
        # why verified_ok doesn't vary by confidence yet).
        points = (
            status_rule
            if isinstance(status_rule, int)
            else status_rule[finding.confidence.level]
        )

        return ScoredFinding(
            check_id=finding.check_id,
            status=finding.status,
            confidence_level=finding.confidence.level,
            points_deducted=points,
            rule_matched=rule_matched,
        )
