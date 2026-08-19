"""Growth Potential schema: the agent's report.

No new raw-extract type here -- GrowthPotentialAgent reads the
opportunity-framed fields (in_growth_corridor, near_major_road_upgrade,
near_approved_layout) already added to KudaMasterPlanExtract
(schemas/zoning.py). Same screenshot, same adapter, two different agents
reading different fields off it -- see that module's docstring for why.
"""

from typing import Literal

from pydantic import Field

from bhoomicheck.schemas.report import BaseAgentReport
from bhoomicheck.schemas.zoning import KudaMasterPlanExtract


class GrowthPotentialReport(BaseAgentReport):
    """Full output contract of the Growth Potential Agent.

    Attributes:
        agent_name: Pinned to "growth_potential" -- a report claiming
            this shape under another agent's name is a validation error.
        extracts: One entry per master-plan screenshot examined -- the
            same KudaMasterPlanExtract ZoningReport uses, just read for
            different fields. At least one is required: this agent only
            runs when a lookup was actually performed, so an empty list
            means a malfunction, not a clean result.
    """

    agent_name: Literal["growth_potential"] = "growth_potential"
    extracts: list[KudaMasterPlanExtract] = Field(min_length=1)
