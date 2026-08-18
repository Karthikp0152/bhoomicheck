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
on LitigationCaseExtract (schemas/litigation.py) is pinned to a fixed
literal so every case extracted here structurally declares itself an
unconfirmed name match, not a verdict about a person. `parse()` still
needs a real eCourts search-result sample before it can be implemented
for real.
"""

from pathlib import Path

from bhoomicheck.adapters.base import ManualAdapter
from bhoomicheck.schemas.litigation import LitigationSearchQuery, LitigationSearchResult


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
