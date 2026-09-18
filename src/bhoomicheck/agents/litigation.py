"""Litigation Agent: eCourts search results -> LitigationReport.

Deterministic, unlike DocumentAnalysisAgent: by the time this runs,
LitigationAdapter.parse() has already turned unstructured eCourts output
into LitigationSearchResult objects (0 or more cases, each with real
fields). There's no free text left to interpret, so mapping that
structured data to Findings needs no model call and no retry loop --
just the guardrail-honoring logic below, which is also easier to test
exactly because it's plain code.
"""

from datetime import date, datetime, timezone
from pathlib import Path

from bhoomicheck.schemas.confidence import Confidence
from bhoomicheck.schemas.finding import Finding
from bhoomicheck.schemas.litigation import LitigationReport, LitigationSearchResult
from bhoomicheck.schemas.parcel import ParcelIdentifier
from bhoomicheck.schemas.provenance import Provenance

SOURCE_NAME = "eCourts (Warangal District Court + Telangana High Court, party-name search)"


class LitigationAgent:
    """Builds a validated LitigationReport from one or more eCourts searches."""

    def report(
        self,
        parcel: ParcelIdentifier,
        searches: list[tuple[Path, LitigationSearchResult]],
    ) -> LitigationReport:
        """Assemble a report from (uploaded file, parsed search result) pairs.

        Args:
            parcel: The parcel this litigation check is for.
            searches: One entry per name variant searched -- the file the
                human uploaded (for provenance) paired with what
                LitigationAdapter.parse() produced from it. The filename
                is a system-known fact fed in by the caller, same as
                DocumentAnalysisAgent's PDF paths -- never guessed here.
        """
        fetched_at = datetime.now(timezone.utc).date()
        findings = [
            self._finding_for(upload_path, result, fetched_at)
            for upload_path, result in searches
        ]
        return LitigationReport(
            parcel=parcel,
            generated_at=datetime.now(timezone.utc),
            searches=[result for _, result in searches],
            findings=findings,
        )

    def _finding_for(
        self, upload_path: Path, result: LitigationSearchResult, fetched_at: date
    ) -> Finding:
        provenance = Provenance(
            source_name=SOURCE_NAME,
            source_type="manual",
            document=upload_path.name,
            fetched_at=fetched_at,
        )

        if not result.cases:
            return Finding(
                check_id="litigation.name_match",
                claim=(
                    f'no cases naming "{result.searched_name}" as a party '
                    "were found in Warangal District Court or Telangana "
                    "High Court eCourts search"
                ),
                status="verified_ok",
                provenance=provenance,
                confidence=Confidence(
                    level="medium",
                    reason=(
                        "name-based search only -- misspellings, untried "
                        "name variants, or filing under a different name "
                        "would not surface here"
                    ),
                ),
            )

        case_summary = "; ".join(
            f"{case.case_no or case.cnr_number or 'unnumbered case'} "
            f"({case.court}, {case.status})"
            for case in result.cases
        )
        return Finding(
            check_id="litigation.name_match",
            claim=(
                f'{len(result.cases)} case(s) naming "{result.searched_name}" '
                f"as a party were found: {case_summary}"
            ),
            status="issue_found",
            provenance=provenance,
            confidence=Confidence(
                level="low",
                reason=(
                    "name match only, per CLAUDE.md's hard guardrail -- not "
                    "confirmed to be the parcel's actual owner/seller; "
                    "requires human verification before treating as a real "
                    "litigation risk"
                ),
            ),
        )
