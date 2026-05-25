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


_BROAD_PATTERNS: frozenset[str] = frozenset({"*", "*@*", "?", "**"})


def load_terms(path: Path, *, allow_broad: bool = False) -> list[TermRow]:
    """Load a CSV or JSON term file.

    CSV (`.csv`): UTF-8, header row required; columns ``value`` (required),
    ``type`` (default ``name``), ``id`` (default ``None``). Extra columns
    ignored. Rows with empty ``value`` are skipped.

    JSON (`.json`): UTF-8 top-level array of objects with the same fields.

    Empty file returns ``[]``. Unknown extension raises ``ValueError``.

    Patterns in the broad set (``*``, ``*@*``, ``?``, ``**``) are rejected
    unless ``allow_broad=True``; see TERMS_CSV.md § Broad-pattern guard.
    """
    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return []
    if suffix == ".csv":
        rows = _parse_csv(raw)
    elif suffix == ".json":
        rows = _parse_json(raw)
    else:
        raise ValueError(f"unsupported terms format: {suffix!r}")
    if not allow_broad:
        for row in rows:
            if row.value in _BROAD_PATTERNS:
                raise ValueError(
                    f"broad pattern {row.value!r} rejected; pass allow_broad "
                    "(--allow-broad-patterns at CLI) to override"
                )
    return rows


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


_WILDCARD_CLASSES: dict[str, tuple[str, str]] = {
    "email": (r"[^\s@,;<>]+", r"[^\s@,;<>]"),
    "name": (r"[^\s,;]+", r"[^\s,;]"),
    "org": (r"[^\s,;]+", r"[^\s,;]"),
    "loc": (r"[^\s,;]+", r"[^\s,;]"),
    "phone": (r"\d+", r"\d"),
    "iban": (r"\d+", r"\d"),
    "cc": (r"\d+", r"\d"),
    "ssn": (r"\d+", r"\d"),
}
_DEFAULT_WILDCARDS: tuple[str, str] = (r"\S+", r"\S")


def _is_pattern(value: str) -> bool:
    """``value`` contains an unescaped ``*`` or ``?``."""
    i = 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            i += 2
            continue
        if value[i] in ("*", "?"):
            return True
        i += 1
    return False


def _compile_pattern(row: TermRow) -> re.Pattern[str]:
    """Translate a wildcard ``TermRow`` into a compiled regex.

    Type-aware per TERMS_CSV.md § Wildcard patterns table.
    """
    star, question = _WILDCARD_CLASSES.get(row.type, _DEFAULT_WILDCARDS)
    parts: list[str] = []
    i = 0
    while i < len(row.value):
        ch = row.value[i]
        if ch == "\\" and i + 1 < len(row.value):
            parts.append(re.escape(row.value[i + 1]))
            i += 2
        elif ch == "*":
            parts.append(star)
            i += 1
        elif ch == "?":
            parts.append(question)
            i += 1
        else:
            parts.append(re.escape(ch))
            i += 1
    return re.compile(
        rf"\b{''.join(parts)}\b", flags=re.IGNORECASE | re.UNICODE
    )


def detect_terms(text: str, terms: list[TermRow]) -> Iterator[Span]:
    r"""Yield ``Span`` for every term that matches ``text``.

    Literal matching: ``\b…\b`` Unicode word boundary, case-insensitive
    via ``re.IGNORECASE``. Wildcard patterns are translated to regex
    per the type-aware table in TERMS_CSV.md § Wildcard patterns; a
    pattern Span has ``detector="pattern"`` instead of ``"literal"``.
    """
    for row in terms:
        if _is_pattern(row.value):
            pattern = _compile_pattern(row)
            detector = "pattern"
        else:
            pattern = re.compile(
                rf"\b{re.escape(row.value)}\b", flags=re.IGNORECASE | re.UNICODE
            )
            detector = "literal"
        for match in pattern.finditer(text):
            yield Span(
                start=match.start(),
                end=match.end(),
                text=match.group(0),
                type=row.type,
                detector=detector,
                id=row.id,
            )
