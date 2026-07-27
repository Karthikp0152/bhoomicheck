"""Entry point: run the Document Analysis Agent from the terminal.

Usage:
    python -m bhoomicheck deed.pdf ec.pdf

Asks for the parcel's survey number, village, mandal, and district
interactively, runs the Document Analysis Agent, scores its findings
against scoring/rules.yaml, and prints the report, the risk assessment,
and the mandatory disclaimer as JSON to stdout.
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from bhoomicheck.agents.document_analysis import DocumentAnalysisAgent
from bhoomicheck.agents.gemini import GeminiProvider
from bhoomicheck.schemas.assessment import DISCLAIMER
from bhoomicheck.schemas.parcel import ParcelIdentifier
from bhoomicheck.scoring.engine import evaluate, load_rules


def main() -> int:
    """Parse the PDF paths, prompt for parcel details, run the agent, score, print."""
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

    # Scoring is pure mechanics over the agent's own findings (scoring/
    # engine.py principle 5) — the judgment already happened in the agent;
    # this step only applies the auditable rules in rules.yaml to it.
    assessment = evaluate(report.findings, load_rules())

    print("=== Document Analysis Report ===")
    print(report.model_dump_json(indent=2))
    print()
    print("=== Risk Assessment ===")
    print(assessment.model_dump_json(indent=2))
    print()
    print(DISCLAIMER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
