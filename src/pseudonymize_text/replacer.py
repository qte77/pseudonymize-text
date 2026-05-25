"""Span dedup + right-to-left substitution (ARCHITECTURE.md → replacer.py)."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass


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


def apply_spans(
    text: str, spans: Iterable[Span], get_token: Callable[[Span], str]
) -> str:
    """Return ``text`` with each accepted span replaced by ``get_token(span)``.

    Substitution is single-pass and right-to-left: spans are processed in
    descending ``start`` order so each replacement leaves earlier offsets
    valid. Empty span input returns ``text`` unchanged.

    Overlap precedence (literal > structured > NER, longer wins) and
    ``--ignore`` suppression are introduced in later Red/Green cycles.
    """
    ordered = sorted(spans, key=lambda s: s.start, reverse=True)
    if not ordered:
        return text
    result = text
    for span in ordered:
        result = result[: span.start] + get_token(span) + result[span.end :]
    return result
