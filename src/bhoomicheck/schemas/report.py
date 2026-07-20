"""BaseAgentReport: the contract every specialist agent's output honors.

Specialist agents subclass this and add their own typed fields; the
orchestrator and risk agent handle any report through the base type
(architecture principle 1).
"""

from datetime import datetime

from pydantic import BaseModel, Field

from bhoomicheck.schemas.finding import Finding
from bhoomicheck.schemas.parcel import ParcelIdentifier


class BaseAgentReport(BaseModel):
    """Common shape of every agent's report.

    Attributes:
        agent_name: Which specialist produced this report.
        parcel: The parcel the report is about.
        generated_at: When the report was produced. A full datetime, not a
            date: two runs on the same day must stay distinguishable.
        findings: Every claim the agent checked. At least one entry is
            required — an agent with "nothing to say" must say so
            explicitly via not_verified findings, because an empty report
            is indistinguishable from a silent failure (principle 6).
    """

    agent_name: str = Field(min_length=1)
    parcel: ParcelIdentifier
    generated_at: datetime
    findings: list[Finding] = Field(min_length=1)
