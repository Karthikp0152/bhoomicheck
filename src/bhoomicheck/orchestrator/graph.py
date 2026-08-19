"""Orchestrator: wires the specialist agents into one LangGraph pipeline.

document_analysis, zoning, litigation, and land_records run in parallel --
none of them depend on each other's output. LangGraph runs risk_report
only once all four of its inbound edges have completed (a "join"), so it
always sees every specialist report before assembling the final
RiskReport.

This is a skeleton, not the full orchestrator CLAUDE.md describes: the
adapters' parse() methods are still stubbed (no real KUDA/eCourts/Bhu
Bharati sample yet), so zoning, litigation, and land_records take
pre-parsed extract objects as input here rather than driving the actual
"ask a human, wait for their upload" step themselves. That pause/resume
behavior is exactly what LangGraph's checkpointing and interrupts are
for -- this skeleton doesn't use them yet because there's nothing real to
pause for until parse() exists.
"""

from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from bhoomicheck.agents.document_analysis import DocumentAnalysisAgent
from bhoomicheck.agents.land_records import LandRecordsAgent
from bhoomicheck.agents.litigation import LitigationAgent
from bhoomicheck.agents.risk_report import RiskReportAgent
from bhoomicheck.agents.zoning import ZoningAgent
from bhoomicheck.schemas.document import DocumentAnalysisReport
from bhoomicheck.schemas.land_records import LandRecordExtract, LandRecordsReport
from bhoomicheck.schemas.litigation import LitigationReport, LitigationSearchResult
from bhoomicheck.schemas.parcel import ParcelIdentifier
from bhoomicheck.schemas.risk_report import RiskReport
from bhoomicheck.schemas.zoning import KudaMasterPlanExtract, ZoningReport


class OrchestratorState(TypedDict):
    """Shared state every node reads from and writes back into.

    A TypedDict, not a Pydantic model: this is LangGraph's own convention
    for graph state (every tutorial and the library's internals assume
    it), separate from the Pydantic validation each agent still does on
    its own output. The *outputs* below stay fully validated schemas --
    only the container that carries them between nodes is a plain dict.

    Attributes:
        parcel: The parcel being checked -- shared by every node.
        pdf_paths: Uploaded documents for DocumentAnalysisAgent.
        zoning_inputs: (uploaded screenshot, parsed extract) pairs for
            ZoningAgent -- pre-parsed, since KudaMasterPlanAdapter.parse()
            is still stubbed.
        litigation_inputs: Same idea, for LitigationAgent.
        land_records_inputs: Same idea, for LandRecordsAgent.
        document_report / zoning_report / litigation_report /
            land_records_report: Filled in by their respective nodes;
            None until that node has run.
        final_report: Filled in by the risk_report node once all four
            specialist reports exist.
    """

    parcel: ParcelIdentifier
    pdf_paths: list[Path]
    zoning_inputs: list[tuple[Path, KudaMasterPlanExtract]]
    litigation_inputs: list[tuple[Path, LitigationSearchResult]]
    land_records_inputs: list[tuple[Path, LandRecordExtract]]
    document_report: DocumentAnalysisReport | None
    zoning_report: ZoningReport | None
    litigation_report: LitigationReport | None
    land_records_report: LandRecordsReport | None
    final_report: RiskReport | None


class Orchestrator:
    """Runs document_analysis, zoning, litigation, and land_records, then risk_report."""

    def __init__(
        self,
        document_agent: DocumentAnalysisAgent,
        zoning_agent: ZoningAgent | None = None,
        litigation_agent: LitigationAgent | None = None,
        land_records_agent: LandRecordsAgent | None = None,
        risk_report_agent: RiskReportAgent | None = None,
    ) -> None:
        """
        Args:
            document_agent: No default -- it needs an LLMProvider (a real
                GeminiProvider, or a FakeProvider in tests), and guessing
                which one silently would hide a real dependency.
            zoning_agent, litigation_agent, land_records_agent,
                risk_report_agent: Default to plain instances since
                they're deterministic and take no provider; overridable
                for tests that want a fixture RiskScorer, same as
                RiskReportAgent's own default pattern.
        """
        self.document_agent = document_agent
        self.zoning_agent = zoning_agent or ZoningAgent()
        self.litigation_agent = litigation_agent or LitigationAgent()
        self.land_records_agent = land_records_agent or LandRecordsAgent()
        self.risk_report_agent = risk_report_agent or RiskReportAgent()
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(OrchestratorState)
        builder.add_node("document_analysis", self._document_analysis_node)
        builder.add_node("zoning", self._zoning_node)
        builder.add_node("litigation", self._litigation_node)
        builder.add_node("land_records", self._land_records_node)
        builder.add_node("risk_report", self._risk_report_node)

        # Fan out: all four specialist nodes start together from START.
        builder.add_edge(START, "document_analysis")
        builder.add_edge(START, "zoning")
        builder.add_edge(START, "litigation")
        builder.add_edge(START, "land_records")
        # Fan in: risk_report has four inbound edges, so LangGraph only
        # runs it once every specialist node is done.
        builder.add_edge("document_analysis", "risk_report")
        builder.add_edge("zoning", "risk_report")
        builder.add_edge("litigation", "risk_report")
        builder.add_edge("land_records", "risk_report")
        builder.add_edge("risk_report", END)
        return builder.compile()

    def _document_analysis_node(self, state: OrchestratorState) -> dict:
        report = self.document_agent.analyze(state["parcel"], state["pdf_paths"])
        return {"document_report": report}

    def _zoning_node(self, state: OrchestratorState) -> dict:
        report = self.zoning_agent.report(state["parcel"], state["zoning_inputs"])
        return {"zoning_report": report}

    def _litigation_node(self, state: OrchestratorState) -> dict:
        report = self.litigation_agent.report(state["parcel"], state["litigation_inputs"])
        return {"litigation_report": report}

    def _land_records_node(self, state: OrchestratorState) -> dict:
        report = self.land_records_agent.report(state["parcel"], state["land_records_inputs"])
        return {"land_records_report": report}

    def _risk_report_node(self, state: OrchestratorState) -> dict:
        reports = [
            state["document_report"],
            state["zoning_report"],
            state["litigation_report"],
            state["land_records_report"],
        ]
        final = self.risk_report_agent.assemble(state["parcel"], reports)
        return {"final_report": final}

    def run(
        self,
        parcel: ParcelIdentifier,
        pdf_paths: list[Path],
        zoning_inputs: list[tuple[Path, KudaMasterPlanExtract]],
        litigation_inputs: list[tuple[Path, LitigationSearchResult]],
        land_records_inputs: list[tuple[Path, LandRecordExtract]],
    ) -> RiskReport:
        """Run the full pipeline and return the final RiskReport."""
        result = self._graph.invoke(
            {
                "parcel": parcel,
                "pdf_paths": pdf_paths,
                "zoning_inputs": zoning_inputs,
                "litigation_inputs": litigation_inputs,
                "land_records_inputs": land_records_inputs,
                "document_report": None,
                "zoning_report": None,
                "litigation_report": None,
                "land_records_report": None,
                "final_report": None,
            }
        )
        return result["final_report"]
