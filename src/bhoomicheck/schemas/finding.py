"""Finding: a single checked claim, with its evidence and trust level.

The atomic unit of every agent report. Composes Provenance (principle 3)
and Confidence (principle 4), and encodes principle 6: a check that could
not be performed is "not_verified", never a silent "no problem found".
"""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from bhoomicheck.schemas.confidence import Confidence
from bhoomicheck.schemas.provenance import Provenance

# The risk families scoring rules match on. Rules cannot reliably match
# prose claims, so every finding must self-classify into one of these;
# "other" exists so an unanticipated risk is never forced into a wrong
# bucket (scoring handles it via defaults).
FindingCategory = Literal[
    "ownership",
    "deed_chain",
    "mortgage",
    "litigation",
    "prohibited_land",
    "master_plan_road",
    "ftl_buffer",
    "other",
]


class Finding(BaseModel):
    """One verified, problematic, or unverifiable claim about a parcel.

    Attributes:
        claim: The statement that was checked, e.g. "survey no. 123/A is
            not listed in the prohibited-lands register".
        category: Which risk family the claim belongs to — the hook the
            scoring rules match on (principle 5).
        status: Outcome of the check. "not_verified" is a first-class
            outcome so missing data can never masquerade as good news.
        provenance: Where the supporting fact came from. Required unless
            the check never reached a source (status "not_verified").
        confidence: The agent's trust in this finding, with its reason.
    """

    claim: str = Field(min_length=1)
    category: FindingCategory
    status: Literal["verified_ok", "issue_found", "not_verified"]
    provenance: Provenance | None = None
    confidence: Confidence

    @model_validator(mode="after")
    def require_provenance_when_checked(self) -> Self:
        # A verified-ok or issue-found status asserts something about the
        # world, so it must cite a source. Only "not_verified" may lack
        # provenance — there, the absence of a source *is* the finding.
        if self.status != "not_verified" and self.provenance is None:
            raise ValueError(
                f"status {self.status!r} requires provenance; "
                "only 'not_verified' findings may omit it"
            )
        return self
