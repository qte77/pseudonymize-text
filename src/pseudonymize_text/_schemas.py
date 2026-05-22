"""Pydantic schemas for persisted artefacts (HASHING.md §10)."""

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class MappingRecord(BaseModel):
    """One entry in the mapping JSON file (HASHING.md §10)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: str
    canonical: str
    type: str
    id: str | None
    first_seen: AwareDatetime
    last_seen: AwareDatetime
    occurrences: int = Field(ge=1)
