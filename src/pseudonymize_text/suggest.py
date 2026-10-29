"""Candidate term discovery for `pseudonymize suggest-terms` (issue #106).

Aggregates NER spans into ``terms.csv``-ready rows for the operator to review.
Suggestions are never applied: no output tree, mapping, or report is written.
"""

import csv
import io
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from .detectors.terms import TermRow, detect_terms
from .replacer import Span


@dataclass(frozen=True)
class Candidate:
    """One suggested term row: surface ``value``, entity ``type``, occurrences."""

    value: str
    type: str
    count: int


def suggest_terms(spans: Iterable[Span], terms: list[TermRow]) -> list[Candidate]:
    """Dedupe ``spans`` into candidates not already covered by ``terms``.

    Whitespace is collapsed and the dedupe key is ``(casefold(value), type)``;
    the first-seen surface form is kept. A value that an existing term (literal
    or pattern) matches in full is dropped. Sorted by count descending, then
    value, then type.
    """
    counts: Counter[tuple[str, str]] = Counter()
    surface: dict[tuple[str, str], str] = {}
    for span in spans:
        value = " ".join(span.text.split())
        if not value or _covered(value, terms):
            continue
        key = (value.casefold(), span.type)
        surface.setdefault(key, value)
        counts[key] += 1
    candidates = [Candidate(surface[k], k[1], n) for k, n in counts.items()]
    return sorted(candidates, key=lambda c: (-c.count, c.value.casefold(), c.type))


def _covered(value: str, terms: list[TermRow]) -> bool:
    return any(s.start == 0 and s.end == len(value) for s in detect_terms(value, terms))


def format_candidates_csv(candidates: Iterable[Candidate]) -> str:
    """Render ``candidates`` as CSV with header ``value,type,id,count``.

    ``id`` is left empty for the operator; ``load_terms`` ignores ``count``,
    so the file loads as a term list once reviewed.
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["value", "type", "id", "count"])
    for c in candidates:
        writer.writerow([c.value, c.type, "", c.count])
    return buf.getvalue()
