"""Zoning schemas: raw master-plan extract and the Zoning Agent's report.

KudaMasterPlanExtract was originally defined in adapters/kuda.py, but
ZoningReport needs to embed it, and schemas should never depend on
adapters (the reverse is already true -- e.g. KudaMasterPlanAdapter
imports ParcelIdentifier from here). Moving it here mirrors
schemas/document.py and schemas/litigation.py, which do the same for the
same reason.
"""

from typing import Literal

from pydantic import BaseModel, Field

from bhoomicheck.schemas.report import BaseAgentReport


class KudaMasterPlanExtract(BaseModel):
    """Raw fields expected off a zoomed-in 1acre.in master-plan screenshot.

    PROVISIONAL -- see adapters/kuda.py module docstring. Every field is
    optional because we don't yet know which of these are actually
    legible on a screenshot; nobody has supplied a real sample yet.

    Attributes:
        zoning_classification: e.g. "residential", "commercial" -- exact
            vocabulary 1acre/KUDA uses is unconfirmed, so this stays free
            text rather than a Literal for now.
        road_widening_affects_parcel: Whether a master-plan road passes
            through or borders the parcel, forcing a setback surrender --
            this is the central risk from CLAUDE.md's problem statement.
        setback_required_meters: Width of land the owner would have to
            surrender, if visible/labeled on the map.
        within_ftl_buffer: Whether the parcel falls inside a lake Full
            Tank Level buffer zone.
        notes: Anything else visible that doesn't fit a structured field.
    """

    zoning_classification: str | None = None
    road_widening_affects_parcel: bool | None = None
    setback_required_meters: float | None = None
    within_ftl_buffer: bool | None = None
    notes: str | None = None


class ZoningReport(BaseAgentReport):
    """Full output contract of the Zoning Agent.

    Inherits the base contract (parcel, findings, timestamp) and adds the
    raw master-plan extracts the findings were built from.

    Attributes:
        agent_name: Pinned to "zoning" -- a report claiming this shape
            under another agent's name is a validation error.
        extracts: One entry per master-plan screenshot examined. At least
            one is required: this agent only runs when a lookup was
            actually performed, so an empty list means a malfunction, not
            a clean result.
    """

    agent_name: Literal["zoning"] = "zoning"
    extracts: list[KudaMasterPlanExtract] = Field(min_length=1)
