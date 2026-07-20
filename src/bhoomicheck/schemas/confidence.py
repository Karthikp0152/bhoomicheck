"""Confidence: how much an agent trusts a finding, and why.

Every finding carries one of these (architecture principle 4). Records
migrated from Dharani to Bhu Bharati are often messy; an agent that cannot
express uncertainty lies.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Three discrete levels instead of a 0-1 score: LLM-produced numbers imply
# precision we don't have, and discrete levels keep scoring/rules.yaml
# auditable ("low confidence on ownership -> flag for manual check").
ConfidenceLevel = Literal["high", "medium", "low"]


class Confidence(BaseModel):
    """An agent's self-assessed trust in a single finding.

    Attributes:
        level: Discrete trust level.
        reason: Why the agent chose this level, e.g. "extent differs
            between Dharani and Bhu Bharati records". A bare level without
            a reason is unauditable, so this is required and non-empty.
    """

    level: ConfidenceLevel
    reason: str = Field(min_length=1)
