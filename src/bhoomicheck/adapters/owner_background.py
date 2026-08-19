"""OwnerBackgroundAdapter: manual-mode adapter for IGRS Telangana lookups.

Real government portal, confirmed via search (not guessed):
  https://registration.telangana.gov.in/ (IGRS Telangana -- Registration
  and Stamps Department). Online Services offers "Certified Copies" (pull
  up a specific registered document by its number, including a Power of
  Attorney) and "Encumbrance Search" (search by property details to see
  the registered document chain for a survey number).

This agent exists specifically because of a well-established legal trap:
*Suraj Lamp & Industries v. State of Haryana* (Supreme Court, 2011) held
that Power-of-Attorney/Agreement-to-Sell/Will transactions do not validly
transfer title -- only a registered sale deed does. A seller transacting
via GPA, or a GPA that turns out to be unregistered or revoked, is a real
risk this project's problem statement is built to catch, not a
hypothetical.

Query is keyed by a person's name (like litigation), not a parcel -- see
adapters/base.py, which is why ManualAdapter is generic over the query
type at all.

STILL PROVISIONAL: `OwnerBackgroundExtract` (schemas/owner_background.py)
is a best-effort guess at what's legible in an IGRS lookup result --
nobody has supplied a real sample yet. `parse()` refuses to run until
one exists.
"""

from pathlib import Path

from bhoomicheck.adapters.base import ManualAdapter
from bhoomicheck.schemas.owner_background import OwnerBackgroundExtract, OwnerBackgroundQuery


class OwnerBackgroundAdapter(ManualAdapter[OwnerBackgroundQuery, OwnerBackgroundExtract]):
    """Manual-mode adapter: IGRS Telangana registered-document lookup.

    `instructions()` points at the real, confirmed portal. `parse()`
    still needs a real result sample before it can be implemented -- it
    fails loudly instead of guessing at layout nobody has seen.
    """

    source_name = "IGRS Telangana (registration.telangana.gov.in)"

    def instructions(self, query: OwnerBackgroundQuery) -> str:
        poa_step = (
            f'2. Since a Power of Attorney document number is known ("{query.poa_document_no}"), '
            "use Online Services -> Certified Copies, enter that document "
            "number, and confirm: is it a genuinely registered document? "
            "What does it actually authorize? Is there any indication "
            "it's been revoked?\n"
            if query.poa_document_no
            else "2. Ask whether this transaction involves a Power of "
            "Attorney at all -- if so, get its registration document "
            "number and repeat this lookup with it.\n"
        )
        return (
            "https://registration.telangana.gov.in/\n"
            f'1. Search for registered documents naming "{query.seller_name}" '
            "as a party, using Online Services -> Encumbrance Search "
            "(by property details) or Certified Copies (by document "
            "number, if known).\n"
            f"{poa_step}"
            "3. Check whether the name on any registered sale deed for "
            f'this property actually matches "{query.seller_name}" -- a '
            "mismatch is a red flag independent of any POA question.\n"
            "4. Remember: per Suraj Lamp v. State of Haryana (Supreme "
            "Court), a GPA/Agreement-to-Sell/Will alone never transfers "
            "title -- only a registered sale deed does. If the chain "
            "relies on a GPA with no proper sale deed after it, that is "
            "itself the finding, not something to explain away.\n"
            "5. Take a screenshot of every result and upload it here."
        )

    def parse(self, upload_path: Path) -> OwnerBackgroundExtract:
        raise NotImplementedError(
            "OwnerBackgroundAdapter.parse() has no real IGRS result sample "
            "to learn its shape from yet -- provide a screenshot before "
            "this can be implemented (fail loudly rather than guess at "
            "parsing logic, per CLAUDE.md principle 6)."
        )
