"""Entry point: run the full BhoomiCheck pipeline from the terminal.

Usage:
    python -m bhoomicheck --survey-no 123/A --village Hasanparthy \
        --mandal Hasanparthy --district Warangal \
        --seller-name "K. Rajaiah" [--seller-aka "Rajaiah Kondapaka"] \
        [--poa-document-no GPA/456/2020] \
        deed.pdf ec.pdf

Runs Document Analysis immediately (its PDFs are supplied up front), then
walks through zoning, litigation, land_records, and owner_background one
at a time: each prints its adapter's instructions() text, asks for the
path to the file you fetched by hand, and continues once you provide it.
growth_potential and risk_report run automatically once their inputs are
ready -- no separate prompt.

Single-session only: state lives in memory (Orchestrator's default
InMemorySaver), so this can't be paused, the terminal closed, and resumed
days later the way the real manual-adapter workflow is meant to work --
that needs a persistent checkpointer, not built yet. Have every file
ready before starting, or expect to re-run from scratch.

Known limitation, stated honestly rather than hidden: every manual
adapter's parse() still raises NotImplementedError (no real KUDA/eCourts/
Bhu Bharati/IGRS sample yet) -- providing any upload path will currently
stop the run with that error. This entry point is real and usable for
document analysis alone today; the rest becomes usable once those
parse() methods are.

Prints the validated RiskReport as JSON to stdout.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from bhoomicheck.agents.document_analysis import DocumentAnalysisAgent
from bhoomicheck.agents.gemini import GeminiProvider
from bhoomicheck.orchestrator.graph import Orchestrator, PendingUpload
from bhoomicheck.schemas.litigation import LitigationSearchQuery
from bhoomicheck.schemas.owner_background import OwnerBackgroundQuery
from bhoomicheck.schemas.parcel import ParcelIdentifier
from bhoomicheck.schemas.risk_report import RiskReport


def _resolve_pending(
    orchestrator: Orchestrator, thread_id: str, result: list[PendingUpload] | RiskReport
) -> RiskReport:
    """Walk through every pending manual lookup, one at a time, via stdin."""
    while isinstance(result, list):
        pending = result[0]
        print(f"\n=== {pending.agent} needs a manual lookup ===")
        print(pending.instructions)
        while True:
            path_str = input(f"\nPath to the uploaded file for {pending.agent}: ").strip()
            upload_path = Path(path_str)
            if upload_path.is_file():
                break
            print(f'"{path_str}" is not a file -- try again.')
        result = orchestrator.provide_upload(thread_id, pending.interrupt_id, upload_path)
    return result


def main() -> int:
    """Parse arguments, run the pipeline (prompting for manual uploads), print the report."""
    # Entry point owns process setup: .env is loaded here, once, and
    # nowhere else — library code never mutates the environment.
    load_dotenv()

    parser = argparse.ArgumentParser(prog="bhoomicheck")
    parser.add_argument("--survey-no", required=True)
    parser.add_argument("--village", required=True)
    parser.add_argument("--mandal", required=True)
    parser.add_argument("--district", default="Warangal")
    parser.add_argument(
        "--seller-name", required=True, help="name to search for litigation/owner-background checks"
    )
    parser.add_argument(
        "--seller-aka", nargs="*", default=[], help="spelling variants/short forms to also search"
    )
    parser.add_argument(
        "--poa-document-no", default=None, help="Power of Attorney document number, if already known"
    )
    parser.add_argument("pdfs", nargs="+", type=Path, help="document PDF(s) for Document Analysis")
    args = parser.parse_args()

    missing = [p for p in args.pdfs if not p.is_file()]
    if missing:
        parser.error(f"file(s) not found: {', '.join(map(str, missing))}")

    parcel = ParcelIdentifier(
        survey_no=args.survey_no,
        village=args.village,
        mandal=args.mandal,
        district=args.district,
    )
    orchestrator = Orchestrator(document_agent=DocumentAnalysisAgent(GeminiProvider()))
    # One thread_id per invocation -- see module docstring on why this
    # can't be resumed across separate process runs yet.
    thread_id = f"{args.survey_no}-{datetime.now(timezone.utc).isoformat()}"

    try:
        result = orchestrator.start(
            thread_id=thread_id,
            parcel=parcel,
            pdf_paths=args.pdfs,
            litigation_query=LitigationSearchQuery(
                full_name=args.seller_name, also_known_as=args.seller_aka
            ),
            owner_background_query=OwnerBackgroundQuery(
                seller_name=args.seller_name, poa_document_no=args.poa_document_no
            ),
        )
        report = _resolve_pending(orchestrator, thread_id, result)
    except NotImplementedError as e:
        # Fail loudly, but without a raw traceback for a limitation the
        # module docstring already explains: an adapter's parse() isn't
        # implemented yet, not a bug in this run.
        print(f"\nStopped: {e}", file=sys.stderr)
        return 1

    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
