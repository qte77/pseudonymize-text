"""Pydantic schemas for persisted artefacts (HASHING.md §10, ARCHITECTURE.md Report Schema)."""

from typing import Literal

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


class ReportHeader(BaseModel):
    """First line of every report JSONL (ARCHITECTURE.md → Report Schema)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_: Literal["pseudonymize.report/1"] = Field(alias="schema")
    tool_version: str
    started_at: AwareDatetime
    config_hash: str = Field(pattern=r"^[0-9a-f]{32}$")


class ReportRecord(BaseModel):
    """One detected span in the report JSONL (ARCHITECTURE.md → Report Schema)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    file: str
    line: int = Field(ge=1)
    col: int = Field(ge=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str
    detector: str = Field(pattern=r"^(literal|pattern|structured:[a-z]+|phi:[a-z]+|ner:[A-Z]+)$")
    type: str
    id: str | None
    token: str = Field(pattern=r"^<[A-Z]+:[0-9a-f]{32}>$")
    confidence: float | None = None
    context: str
