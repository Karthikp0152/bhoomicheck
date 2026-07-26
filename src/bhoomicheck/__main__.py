"""Entry point: run the Document Analysis Agent from the terminal.

Usage:
    python -m bhoomicheck deed.pdf ec.pdf

Asks for the parcel's survey number, village, mandal, and district
interactively, then prints the validated DocumentAnalysisReport as JSON
to stdout.
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from bhoomicheck.agents.document_analysis import DocumentAnalysisAgent
from bhoomicheck.agents.gemini import GeminiProvider
from bhoomicheck.schemas.parcel import ParcelIdentifier


def main() -> int:
    """Parse the PDF paths, prompt for parcel details, run the agent, print the report."""
    # Entry point owns process setup: .env is loaded here, once, and
    # nowhere else — library code never mutates the environment.
    load_dotenv()

    parser = argparse.ArgumentParser(prog="bhoomicheck")
    parser.add_argument("pdfs", nargs="+", type=Path, help="document PDF(s)")
    args = parser.parse_args()

    missing = [p for p in args.pdfs if not p.is_file()]
    if missing:
        parser.error(f"file(s) not found: {', '.join(map(str, missing))}")

    # Prompted rather than flagged: this tool checks one parcel at a time,
    # so asking is friendlier than remembering four --flag names.
    survey_no = input("Survey number: ").strip()
    village = input("Village: ").strip()
    mandal = input("Mandal: ").strip()
    district = input("District [Warangal]: ").strip() or "Warangal"

    parcel = ParcelIdentifier(
        survey_no=survey_no,
        village=village,
        mandal=mandal,
        district=district,
    )
    agent = DocumentAnalysisAgent(GeminiProvider())
    report = agent.analyze(parcel, args.pdfs)
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
