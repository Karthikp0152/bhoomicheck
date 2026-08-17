"""LitigationAdapter: manual-mode adapter for eCourts party-name searches.

Both real government portals confirmed via search (not guessed):
  https://warangal.dcourts.gov.in/case-status-search-by-petitioner-respondent/
  https://hcservices.ecourts.gov.in/ (Case Status -> Search by
  Petitioner/Respondent Name -> Telangana)

Both require solving a captcha to search, which is exactly the situation
CLAUDE.md's hard guardrail exists for: we never automate around a
captcha, so this stays manual-only -- a human runs the search themselves
and hands back what the portal showed.

Litigation search is keyed by a person's name, not a parcel (unlike KUDA
master plan) -- that mismatch is why ManualAdapter became generic over
the query type, not just the raw-record type. See adapters/base.py.

The other hard guardrail this file exists to enforce: a name match on a
court listing is never proof the case involves the parcel's actual owner
-- common Indian names produce false positives constantly. `match_basis`
is pinned to a fixed literal so every case extracted here structurally
declares itself an unconfirmed name match, not a verdict about a person.
`parse()` still needs a real eCourts search-result sample before it can
be implemented for real.
"""

from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from bhoomicheck.adapters.base import ManualAdapter


class LitigationSearchQuery(BaseModel):
    """The person being checked, and name variants worth trying.

    Attributes:
        full_name: The name to search, as it appears on the land record
            being checked (e.g. a sale deed's executant).
        also_known_as: Spelling variants/short forms worth trying too --
            eCourts matches partial names (3+ characters), and
            transliterated Indian names vary a lot across documents.
    """

    full_name: str
    also_known_as: list[str] = []


class LitigationCaseExtract(BaseModel):
    """One case record as printed on an eCourts party-name search result.

    Every field reflects what the listing showed, not a conclusion about
    the parcel or its owner -- see module docstring on match_basis.

    Attributes:
        court: Which court this case is in, e.g. "District Court,
            Warangal" or "High Court for the State of Telangana".
        case_no: The case's registration number, if shown.
        cnr_number: eCourts' own unique case identifier, if shown.
        case_type: Free text (e.g. "Original Suit", "Civil Appeal") --
            vocabulary varies by court, so not a Literal.
        status: Pending/disposed, mirroring the portal's own search filter.
        filing_date: Date the case was filed, if shown.
        matched_party_name: The exact name string the portal displayed
            for the party that matched the search -- may differ from the
            searched name (partial match, different transliteration).
        party_role: e.g. "Petitioner", "Respondent", if shown.
        match_basis: Always "name_search_unconfirmed". Fixed rather than
            left to convention so no downstream code can silently treat
            this as a confirmed identity match (CLAUDE.md hard guardrail).
        notes: Anything else shown that doesn't fit a structured field.
    """

    court: str
    case_no: str | None = None
    cnr_number: str | None = None
    case_type: str | None = None
    status: Literal["pending", "disposed", "unknown"]
    filing_date: date | None = None
    matched_party_name: str
    party_role: str | None = None
    match_basis: Literal["name_search_unconfirmed"] = "name_search_unconfirmed"
    notes: str | None = None


class LitigationSearchResult(BaseModel):
    """Everything found when searching one person's name across eCourts.

    Attributes:
        searched_name: The name actually typed into the search box (one
            of query.full_name / query.also_known_as).
        cases: Every case the search returned. Empty is a valid, useful
            result (no matches found) -- it is not the same as
            "not_verified"; the Litigation Agent decides which finding
            status that maps to, this adapter just reports what it saw.
    """

    searched_name: str
    cases: list[LitigationCaseExtract] = []


class LitigationAdapter(ManualAdapter[LitigationSearchQuery, LitigationSearchResult]):
    """Manual-mode adapter: eCourts party-name search, District + High Court.

    `instructions()` points at real, confirmed portal URLs. `parse()`
    still needs a real search-result sample (screenshot or saved page)
    before it can be implemented -- it fails loudly instead of guessing
    at layout nobody has seen.
    """

    source_name = "eCourts (Warangal District Court + Telangana High Court, party-name search)"

    def instructions(self, query: LitigationSearchQuery) -> str:
        names = ", ".join([query.full_name, *query.also_known_as])
        return (
            "Search for pending or disposed cases naming this person as a "
            f"party. Try each of these name variants: {names} -- eCourts "
            "matches on partial names (3+ characters), so short forms and "
            "spelling variants can surface different results.\n\n"
            "1. Warangal District Court:\n"
            "   https://warangal.dcourts.gov.in/case-status-search-by-petitioner-respondent/\n"
            "   Select Both (pending and disposed), enter a name, solve "
            "the captcha, note every case listed.\n\n"
            "2. Telangana High Court:\n"
            "   https://hcservices.ecourts.gov.in/\n"
            "   Case Status -> Search by Petitioner/Respondent Name -> "
            "select Telangana, enter a name, solve the captcha, note "
            "every case listed.\n\n"
            "Upload a screenshot (or written note) of every case shown "
            "for each name variant tried, including cases you don't "
            "recognize -- do not filter results yourself. Deciding which "
            "matches are plausible is a human-review step later, not "
            "part of running the search."
        )

    def parse(self, upload_path: Path) -> LitigationSearchResult:
        raise NotImplementedError(
            "LitigationAdapter.parse() has no real eCourts search-result "
            "sample to learn its shape from yet -- provide a screenshot "
            "or saved result page before this can be implemented (fail "
            "loudly rather than guess at parsing logic, per CLAUDE.md "
            "principle 6)."
        )
