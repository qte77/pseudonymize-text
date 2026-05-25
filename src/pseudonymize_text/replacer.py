"""Span dedup + right-to-left substitution (ARCHITECTURE.md → replacer.py)."""

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
