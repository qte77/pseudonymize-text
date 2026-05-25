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

    Empty span input returns ``text`` unchanged. Substitution semantics
    (precedence, length-tiebreak, ignore-list, right-to-left rewrite) are
    introduced incrementally by subsequent Red/Green cycles.
    """
    spans_list = list(spans)
    if not spans_list:
        return text
    # R3 will introduce right-to-left substitution; for now the contract
    # is only pinned for the empty-span case.
    raise NotImplementedError(
        f"apply_spans for {len(spans_list)} span(s) using {get_token!r} "
        "lands in R3"
    )
