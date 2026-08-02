"""Scoring engine: findings -> auditable RiskAssessment.

The rules live in rules.yaml, never in code or prompts (principle 5).
This module only loads, validates, and mechanically applies them, so a
lawyer reviewing the YAML has reviewed the actual scoring behaviour.
"""

from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, Field, model_validator

from bhoomicheck.schemas.assessment import (
    SEVERITY_RANK,
    RiskAssessment,
    RiskFlag,
    Severity,
)
from bhoomicheck.schemas.finding import Finding, FindingCategory

# Only these statuses ever flag; verified_ok findings never do.
FlaggableStatus = Literal["issue_found", "not_verified"]

DEFAULT_RULES_PATH = Path(__file__).parent / "rules.yaml"


class Rule(BaseModel):
    """One auditable scoring rule: (category, status) -> severity."""

    category: FindingCategory
    status: FlaggableStatus
    severity: Severity
    rationale: str = Field(min_length=1)


class RuleSet(BaseModel):
    """The validated contents of rules.yaml.

    Attributes:
        version: Schema version of the rules file.
        defaults: Severity per status when no specific rule matches —
            required, so every possible finding has a defined outcome and
            the engine never has to invent one.
        rules: Specific (category, status) overrides.
    """

    version: int
    defaults: dict[FlaggableStatus, Severity]
    rules: list[Rule]

    @model_validator(mode="after")
    def reject_duplicate_rules(self) -> Self:
        # Two rules for the same (category, status) would make the file's
        # meaning depend on ordering — ambiguity has no place in an
        # auditable rules file, so it's a load-time error.
        seen: set[tuple[str, str]] = set()
        for rule in self.rules:
            key = (rule.category, rule.status)
            if key in seen:
                raise ValueError(f"duplicate rule for {key}")
            seen.add(key)
        return self

    def find(self, category: str, status: str) -> Rule | None:
        """Return the specific rule for this pair, if one exists."""
        for rule in self.rules:
            if (rule.category, rule.status) == (category, status):
                return rule
        return None


def load_rules(path: Path = DEFAULT_RULES_PATH) -> RuleSet:
    """Load and validate a rules file, failing loudly on any defect.

    Uses yaml.safe_load: the unsafe loader can construct arbitrary Python
    objects from file content, which is never acceptable for config.
    """
    data = yaml.safe_load(path.read_text())
    return RuleSet.model_validate(data)


def evaluate(findings: list[Finding], ruleset: RuleSet) -> RiskAssessment:
    """Apply the rules to findings and return the parcel's verdict.

    Pure mechanics, no judgment: judgment lives in rules.yaml.
    """
    flags: list[RiskFlag] = []
    for finding in findings:
        if finding.status == "verified_ok":
            continue
        rule = ruleset.find(finding.category, finding.status)
        if rule is not None:
            severity, rationale = rule.severity, rule.rationale
        else:
            severity = ruleset.defaults[finding.status]
            rationale = (
                f"no specific rule for ({finding.category}, {finding.status}); "
                f"default severity for {finding.status} findings applied"
            )
        flags.append(RiskFlag(severity=severity, rationale=rationale, finding=finding))

    flags.sort(key=lambda f: SEVERITY_RANK[f.severity], reverse=True)
    overall: Severity | Literal["clear"] = flags[0].severity if flags else "clear"
    return RiskAssessment(overall=overall, flags=flags)
