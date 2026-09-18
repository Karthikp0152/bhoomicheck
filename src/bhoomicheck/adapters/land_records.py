"""LandRecordsAdapter: manual-mode adapter for Bhu Bharati land status lookups.

Real government portal, confirmed via search (not guessed):
  https://bhubharati.telangana.gov.in/knowLandStatus

Bhu Bharati is the platform that replaced Dharani -- exactly the
migration CLAUDE.md's own problem statement calls out as a source of
messy records. Searched by District -> Mandal -> Village -> Survey
Number, which maps directly onto ParcelIdentifier (unlike litigation,
which needed ManualAdapter to become generic over the query type at all).

A direct fetch to verify page details (captcha/OTP specifics) was
refused by the domain -- same as kuda.in. That doesn't change the design:
every source starts in manual mode regardless (see adapters/base.py), so
this stays manual whether or not a captcha turns out to be present.

STILL PROVISIONAL: `LandRecordExtract` (schemas/land_records.py) is a
best-effort guess at what's legible in a lookup result -- nobody has
supplied a real sample yet. `parse()` refuses to run until one exists.
"""

from pathlib import Path

from bhoomicheck.adapters.base import ManualAdapter
from bhoomicheck.schemas.land_records import LandRecordExtract
from bhoomicheck.schemas.parcel import ParcelIdentifier


class LandRecordsAdapter(ManualAdapter[ParcelIdentifier, LandRecordExtract]):
    """Manual-mode adapter: Bhu Bharati "Know Land Status" lookup.

    `instructions()` points at the real, confirmed portal URL. `parse()`
    still needs a real result screenshot before it can be implemented --
    it fails loudly instead of guessing at layout nobody has seen.
    """

    source_name = "Bhu Bharati (Telangana Integrated Land Records Management System)"

    def instructions(self, parcel: ParcelIdentifier) -> str:
        return (
            "1. Go to https://bhubharati.telangana.gov.in/knowLandStatus\n"
            f"2. Select district {parcel.district}, mandal {parcel.mandal}, "
            f"village {parcel.village}.\n"
            f"3. Enter survey no. {parcel.survey_no} and fetch the land "
            "status.\n"
            "4. Note the pattadar name(s), extent, land type, and "
            "especially whether the parcel is flagged as prohibited/"
            "assigned land -- this is the single most important field on "
            "this source.\n"
            "5. Take a screenshot of the full result and upload it here."
        )

    def parse(self, upload_path: Path) -> LandRecordExtract:
        raise NotImplementedError(
            "LandRecordsAdapter.parse() has no real Bhu Bharati result "
            "sample to learn its shape from yet -- provide a screenshot "
            "before this can be implemented (fail loudly rather than "
            "guess at parsing logic, per CLAUDE.md principle 6)."
        )
