"""ParcelIdentifier: unambiguous identity of one land parcel.

Survey numbers repeat across villages, so a bare "123/A" is ambiguous.
Every agent report pins itself to a full identifier.
"""

from pydantic import BaseModel, Field


class ParcelIdentifier(BaseModel):
    """The revenue-record address of a parcel.

    Attributes:
        survey_no: Survey (or sub-division) number, e.g. "123/A".
        village: Revenue village the survey number belongs to.
        mandal: Mandal (sub-district) of the village.
        district: District, e.g. "Warangal".
    """

    survey_no: str = Field(min_length=1)
    village: str = Field(min_length=1)
    mandal: str = Field(min_length=1)
    district: str = Field(min_length=1)
