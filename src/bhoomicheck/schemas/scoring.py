"""Scoring schemas: ScoredFinding and RiskScore.

Originally defined in scoring/engine.py, but RiskReport (schemas/
risk_report.py) needs to embed them, and schemas should never depend on
another package (the reverse is already true throughout this codebase --
adapters and scoring both import from schemas). Moving them here mirrors
schemas/document.py, schemas/litigation.py, and schemas/zoning.py, which
do the same for the same reason.
"""

from pydantic import BaseModel

from bhoomicheck.schemas.confidence import ConfidenceLevel


class ScoredFinding(BaseModel):
    """One Finding's contribution to the overall score, for audit trails.

    Attributes:
        check_id: Copied from the Finding, so this record is
            self-contained without needing the original Finding nearby.
        points_deducted: How many points this finding cost.
        rule_matched: The check_id whose rule actually applied -- equals
            check_id when rules.yaml has a specific entry for it, or the
            literal "default" when it fell through to the default rule.
            Distinguishing these two matters for auditing: "this scored
            low because of a generic fallback" is a different situation
            from "this scored low because of a rule someone wrote for it
            on purpose".
    """

    check_id: str
    status: str
    confidence_level: ConfidenceLevel
    points_deducted: int
    rule_matched: str


class RiskScore(BaseModel):
    """The overall score for one parcel, plus how it was reached.

    Attributes:
        score: 0-100. Starts at 100 (no issues found) and rules only
            subtract, floored at 0 -- never negative.
        scored_findings: One entry per input Finding, in the same order,
            so score can be reconstructed and audited finding-by-finding.
    """

    score: int
    scored_findings: list[ScoredFinding]
