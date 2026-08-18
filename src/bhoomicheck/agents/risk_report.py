"""Risk/Report Agent: combines every specialist report into one RiskReport.

Deterministic, same reasoning as LitigationAgent and ZoningAgent: by the
time this runs, every specialist report already exists and validated
itself against its own schema. This agent's only job is to pool their
findings, score them with RiskScorer, and assemble the result -- no LLM,
no free text, nothing to interpret.
"""

from datetime import datetime, timezone

from bhoomicheck.schemas.parcel import ParcelIdentifier
from bhoomicheck.schemas.report import BaseAgentReport
from bhoomicheck.schemas.risk_report import RiskReport
from bhoomicheck.scoring.engine import RiskScorer


class RiskReportAgent:
    """Assembles a RiskReport from every specialist report produced so far."""

    def __init__(self, scorer: RiskScorer | None = None) -> None:
        """
        Args:
            scorer: Defaults to a RiskScorer loaded from the real
                rules.yaml. Overridable so tests can score against a
                fixture rules file instead of the shipped one.
        """
        self.scorer = scorer or RiskScorer()

    def assemble(
        self, parcel: ParcelIdentifier, specialist_reports: list[BaseAgentReport]
    ) -> RiskReport:
        """Build the final report a buyer reads, from every specialist report.

        Args:
            parcel: The parcel being checked. Every specialist_reports
                entry must share this same parcel (enforced by
                RiskReport's own validator) -- mixing parcels here would
                be a serious, silent bug.
            specialist_reports: Every ZoningReport/LitigationReport/
                DocumentAnalysisReport (and any future specialist report)
                produced for this parcel.
        """
        all_findings = [
            finding for report in specialist_reports for finding in report.findings
        ]
        risk_score = self.scorer.score(all_findings)
        return RiskReport(
            parcel=parcel,
            generated_at=datetime.now(timezone.utc),
            overall_score=risk_score.score,
            scored_findings=risk_score.scored_findings,
            specialist_reports=specialist_reports,
        )
