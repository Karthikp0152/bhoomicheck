"""Entry point: run the Document Analysis Agent from the terminal.

Usage:
    python -m bhoomicheck --survey-no 123/A --village Hasanparthy \
        --mandal Hasanparthy --district Warangal deed.pdf ec.pdf

Prints the validated DocumentAnalysisReport as JSON to stdout.
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from bhoomicheck.agents.document_analysis import DocumentAnalysisAgent
from bhoomicheck.agents.gemini import GeminiProvider
from bhoomicheck.schemas.parcel import ParcelIdentifier


def main() -> int:
    """Parse arguments, run the agent, print the report."""
    # Entry point owns process setup: .env is loaded here, once, and
    # nowhere else — library code never mutates the environment.
    load_dotenv()

    parser = argparse.ArgumentParser(prog="bhoomicheck")
    parser.add_argument("--survey-no", required=True)
    parser.add_argument("--village", required=True)
    parser.add_argument("--mandal", required=True)
    parser.add_argument("--district", default="Warangal")
    parser.add_argument("pdfs", nargs="+", type=Path, help="document PDF(s)")
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
    agent = DocumentAnalysisAgent(GeminiProvider())
    report = agent.analyze(parcel, args.pdfs)
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
