"""Term-list literal / pattern loader and matcher (TERMS_CSV.md spec)."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TermRow:
    """One row of a parsed term list per TERMS_CSV.md."""

    value: str
    type: str = "name"
    id: str | None = None


def load_terms(path: Path) -> list[TermRow]:
    """Load a CSV or JSON term file.

    CSV (`.csv`): UTF-8, header row required; columns ``value`` (required),
    ``type`` (default ``name``), ``id`` (default ``None``). Extra columns
    ignored. Rows with empty ``value`` are skipped.

    JSON (`.json`): UTF-8 top-level array of objects with the same fields.

    Empty file returns ``[]``. Unknown extension raises ``ValueError``.
    """
    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return []
    if suffix == ".csv":
        return _parse_csv(raw)
    if suffix == ".json":
        return _parse_json(raw)
    raise ValueError(f"unsupported terms format: {suffix!r}")


def _parse_csv(raw: str) -> list[TermRow]:
    reader = csv.DictReader(raw.splitlines())
    return [_row(r.get("value", ""), r.get("type"), r.get("id")) for r in reader if r.get("value")]


def _parse_json(raw: str) -> list[TermRow]:
    data = json.loads(raw)
    return [_row(r.get("value", ""), r.get("type"), r.get("id")) for r in data if r.get("value")]


def _row(value: str, type_: str | None, id_: str | None) -> TermRow:
    return TermRow(
        value=value.strip(),
        type=(type_ or "name").strip(),
        id=id_.strip() if id_ else None,
    )
