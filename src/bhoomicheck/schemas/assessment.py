"""RiskAssessment: the scored verdict for a parcel.

Severity is deliberately bucketed, not numeric: in land due diligence a
single critical issue kills a deal regardless of how clean everything
else is, so the overall verdict is the worst severity present — totals
and averages would hide exactly the findings that matter most.
"""

from typing import Literal

from pydantic import BaseModel, Field

from bhoomicheck.schemas.finding import Finding

Severity = Literal["critical", "high", "medium", "low", "info"]

# Hard guardrail: every report ships with this, no exceptions. Kept next
# to the assessment schema so output code can't plausibly miss it.
DISCLAIMER = (
    "Automated decision-support based on public records that may be "
    "incomplete or outdated. This is not legal advice. Any name-based "
    "court matches are possible, unconfirmed matches requiring human "
    "verification. Consult a licensed advocate before any purchase."
)

# Worst-wins needs an ordering; keep it in one place.
SEVERITY_RANK: dict[str, int] = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class RiskFlag(BaseModel):
    """One finding that contributes risk, with the rule's reasoning.

    Attributes:
        severity: How serious this flag is.
        rationale: Why — carried from the matching rule so every flag in
            a report is traceable to an auditable line in rules.yaml.
        finding: The full underlying finding, provenance and all.
    """

    severity: Severity
    rationale: str = Field(min_length=1)
    finding: Finding


class RiskAssessment(BaseModel):
    """The scored verdict for one parcel.

    Attributes:
        overall: Worst severity among flags, or "clear" when nothing was
            flagged. "clear" is only reachable when every finding was
            verified_ok — not-verified findings always flag (principle 6).
        flags: Every flagged finding, worst first.
    """

    overall: Severity | Literal["clear"]
    flags: list[RiskFlag]
