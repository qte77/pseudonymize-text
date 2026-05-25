"""Span dedup + right-to-left substitution (ARCHITECTURE.md → replacer.py)."""

import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass

_DETECTOR_RANK = {"literal": 0, "structured": 1, "ner": 2}


@dataclass(frozen=True)
class Span:
    """One detected entity. Emitted by detectors, consumed by the replacer.

    Fields follow ARCHITECTURE.md → Report Schema, minus the report-only
    derivations (line/col/token/context). ``id`` and ``confidence`` are
    optional: ``id`` is set when a term-list row had an ``id`` column;
    ``confidence`` is set only by NER spans.
    """

    start: int
    end: int
    text: str
    type: str
    detector: str
    id: str | None = None
    confidence: float | None = None


def _ignore_key(s: str) -> str:
    """NFKC + casefold, the comparison form used by ``--ignore`` matching."""
    return unicodedata.normalize("NFKC", s).casefold()


def _rank(detector: str) -> int:
    """Source rank per ARCHITECTURE.md § Span Precedence (lower wins)."""
    head = detector.split(":", 1)[0]
    return _DETECTOR_RANK.get(head, len(_DETECTOR_RANK))


def _dedup_overlaps(spans: list[Span]) -> list[Span]:
    """Drop any span that overlaps an already-kept higher-priority span.

    Priority key: (rank ASC, length DESC, start ASC). Rank implements
    literal > structured > NER per ARCHITECTURE.md § Span Precedence; the
    DESC length term implements the same-rank tiebreak (longer wins).
    """
    ordered = sorted(
        spans, key=lambda s: (_rank(s.detector), -(s.end - s.start), s.start)
    )
    kept: list[Span] = []
    for span in ordered:
        if any(span.start < k.end and k.start < span.end for k in kept):
            continue
        kept.append(span)
    return kept


def apply_spans(
    text: str,
    spans: Iterable[Span],
    get_token: Callable[[Span], str],
    ignore: Iterable[str] = (),
) -> str:
    """Return ``text`` with each accepted span replaced by ``get_token(span)``.

    Pipeline: overlap dedup (literal > structured > NER, longer wins) →
    ``ignore`` suppression (NFKC + casefold match on each span's surface
    text) → right-to-left single-pass substitution. Empty span input
    returns ``text`` unchanged.
    """
    kept = _dedup_overlaps(list(spans))
    ignore_set = {_ignore_key(entry) for entry in ignore}
    if ignore_set:
        kept = [s for s in kept if _ignore_key(s.text) not in ignore_set]
    if not kept:
        return text
    ordered = sorted(kept, key=lambda s: s.start, reverse=True)
    result = text
    for span in ordered:
        result = result[: span.start] + get_token(span) + result[span.end :]
    return result
