"""KudaMasterPlanAdapter: manual-mode adapter for KUDA master-plan zoning data.

kuda.in itself blocks automated access (confirmed: it 403s even a plain
read-only fetch), and its site offers no documented per-parcel lookup
anyway. The actual source is 1acre.in, a third-party commercial site that
overlays the KUDA Master Plan 2041 on an interactive map:
  https://1acre.in/map-layers/telangana/warangal-masterplan
  https://1acre.in/map-layers/telangana/survey-numbers-telangana

That distinction matters for provenance (architecture principle 3): this
is a third-party visualization of the government master plan, not the
master plan itself. If 1acre's overlay is stale or mis-plotted, that's a
third-party error, not a KUDA one -- so source_name says so explicitly,
and any agent consuming this should weight its confidence accordingly
rather than treating it as an official record.

STILL PROVISIONAL: the URLs and workflow above are now real (verified via
a live fetch + search), but `KudaMasterPlanExtract`'s fields are still a
best-effort guess at what's readable off a zoomed-in map screenshot --
nobody has supplied a sample screenshot yet. `parse()` refuses to run
until one exists, rather than guess at how to read it.
"""

from pathlib import Path

from bhoomicheck.adapters.base import ManualAdapter
from bhoomicheck.schemas.parcel import ParcelIdentifier
from bhoomicheck.schemas.zoning import KudaMasterPlanExtract


class KudaMasterPlanAdapter(ManualAdapter[ParcelIdentifier, KudaMasterPlanExtract]):
    """Manual-mode adapter: KUDA Master Plan 2041, via 1acre.in's overlay.

    PROVISIONAL -- see module docstring. The lookup workflow and URLs are
    confirmed real; `parse()` still needs a real screenshot sample before
    it can be implemented, so it fails loudly instead of guessing at how
    to read a screenshot nobody has seen.
    """

    source_name = "1acre.in (third-party overlay of KUDA Master Plan 2041)"

    def instructions(self, parcel: ParcelIdentifier) -> str:
        return (
            "1. Go to https://1acre.in/map-layers/telangana/warangal-masterplan "
            "and sign in with your mobile number if prompted.\n"
            "2. Use the survey-number layer "
            "(https://1acre.in/map-layers/telangana/survey-numbers-telangana) "
            f"or navigate manually to locate survey no. {parcel.survey_no}, "
            f"{parcel.village} village, {parcel.mandal} mandal, "
            f"{parcel.district} district.\n"
            "3. Zoom in until the parcel and its surrounding zone "
            "colors/road lines are clearly visible.\n"
            "4. Also note, using the map's legend: is the parcel inside a "
            "\"Growth Corridor 1/2\" or \"Village Expansion Zone\"? Is a "
            "proposed Outer Ring Road / Arterial Road upgrade nearby "
            "(without directly crossing the parcel)? Is it near an area "
            "marked \"Approved Layout\"? This same screenshot is used for "
            "both the setback/zoning check and the growth-potential check "
            "-- no separate lookup needed.\n"
            "5. Take a screenshot showing the parcel and its surrounding "
            "zone/road markings, and upload it here."
        )

    def parse(self, upload_path: Path) -> KudaMasterPlanExtract:
        raise NotImplementedError(
            "KudaMasterPlanAdapter.parse() has no real screenshot to learn "
            "its shape from yet -- provide a sample 1acre.in map screenshot "
            "before this can be implemented (fail loudly rather than guess "
            "at parsing logic, per CLAUDE.md principle 6)."
        )
