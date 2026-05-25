"""Term-list literal / pattern loader and matcher (TERMS_CSV.md spec)."""

import csv
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ..replacer import Span


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


def detect_terms(text: str, terms: list[TermRow]) -> Iterator[Span]:
    r"""Yield ``Span`` for every term that matches ``text``.

    Literal matching: ``\b…\b`` Unicode word boundary, case-insensitive
    via ``re.IGNORECASE`` (NFKC normalisation happens at canonicalisation
    time in ``tokenize.canonicalize`` — TERMS_CSV.md cross-reference).
    Pattern (wildcard) expansion lands in T4.
    """
    for row in terms:
        if "*" in row.value or "?" in row.value:
            continue  # patterns land in T4
        pattern = re.compile(
            rf"\b{re.escape(row.value)}\b", flags=re.IGNORECASE | re.UNICODE
        )
        for match in pattern.finditer(text):
            yield Span(
                start=match.start(),
                end=match.end(),
                text=match.group(0),
                type=row.type,
                detector="literal",
                id=row.id,
            )
