"""ManualAdapter: the human-in-the-loop mode of the adapter pattern.

Every government source (Dharani, KUDA master plan, eCourts...) gets one
adapter. Manual is the mode every source starts in -- and the only mode
ever used where a portal sits behind a captcha or OTP, since we never
automate around those (hard guardrail in CLAUDE.md #3). Instead we tell a
human exactly what to fetch, and parse what they hand back.

Generic over two types, not one:
- QueryT: what you search *by*. Most sources are parcel-keyed (KUDA master
  plan, Dharani), but some aren't -- eCourts litigation search is keyed by
  a person's name, not a survey number. Making this a type parameter
  (instead of hardcoding ParcelIdentifier, as the first version of this
  class did) lets one base class fit both without either source faking a
  key it doesn't actually search by.
- RawRecordT: the structured shape a human's upload parses into.

The `api` and `scrape` modes described in CLAUDE.md #2 aren't built yet:
there's no concrete source wired up to inform their shape, and writing
that shape speculatively would be designing for a hypothetical. They get
their own base classes when the first source that needs them exists.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

QueryT = TypeVar("QueryT")
RawRecordT = TypeVar("RawRecordT")


class ManualAdapter(ABC, Generic[QueryT, RawRecordT]):
    """One government source, retrieved by asking a human to fetch it.

    Subclasses pin QueryT to whatever this source is actually searched by
    (a ParcelIdentifier, a person's name, ...) and RawRecordT to whatever
    structured shape the upload parses into (e.g. an encumbrance-
    certificate model) -- that's the adapter's contribution towards an
    eventual Finding, not a Finding itself. Building the Finding (with its
    provenance and confidence) is the calling agent's job, not the
    adapter's.

    Attributes:
        source_name: Human-readable name for provenance, e.g.
            "KUDA Master Plan 2041".
    """

    source_name: str

    @abstractmethod
    def instructions(self, query: QueryT) -> str:
        """Tell the user exactly what to fetch and where from.

        Plain text meant to be shown directly to a human: which portal,
        what to search for, what to download. This is a static
        description, not a network call -- no scraping or requests here.
        """
        ...

    @abstractmethod
    def parse(self, upload_path: Path) -> RawRecordT:
        """Turn the human's uploaded file into this source's structured data."""
        ...
