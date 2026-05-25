"""Tests for the replacer module (issue #9)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pseudonymize_text.replacer import Span, apply_spans


def _naive_substitute(text: str, spans: list[Span], token: str) -> str:
    """Reference impl: left-to-right walk with cursor; assumes spans are
    non-overlapping. Used as the Hypothesis oracle."""
    parts: list[str] = []
    cursor = 0
    for span in sorted(spans, key=lambda s: s.start):
        parts.append(text[cursor : span.start])
        parts.append(token)
        cursor = span.end
    parts.append(text[cursor:])
    return "".join(parts)


@st.composite
def _text_and_non_overlapping_spans(draw: st.DrawFn) -> tuple[str, list[Span]]:
    text = draw(st.text(min_size=1, max_size=50))
    max_spans = min(3, (len(text) + 1) // 2)
    if max_spans == 0:
        return text, []
    n = draw(st.integers(min_value=0, max_value=max_spans))
    if n == 0:
        return text, []
    points = sorted(
        draw(
            st.lists(
                st.integers(min_value=0, max_value=len(text)),
                min_size=2 * n,
                max_size=2 * n,
                unique=True,
            )
        )
    )
    spans: list[Span] = []
    for i in range(n):
        start, end = points[2 * i], points[2 * i + 1]
        spans.append(
            Span(
                start=start,
                end=end,
                text=text[start:end],
                type="name",
                detector="literal",
            )
        )
    return text, spans


@given(_text_and_non_overlapping_spans())
def test_apply_spans_non_overlap_matches_naive_oracle(
    args: tuple[str, list[Span]],
) -> None:
    text, spans = args
    token = "<TOKEN>"
    assert apply_spans(text, spans, lambda _s: token) == _naive_substitute(
        text, spans, token
    )


def test_span_dataclass_shape() -> None:
    span = Span(
        start=0,
        end=8,
        text="John Doe",
        type="name",
        detector="literal",
    )
    assert span.start == 0
    assert span.end == 8
    assert span.text == "John Doe"
    assert span.type == "name"
    assert span.detector == "literal"
    assert span.id is None
    assert span.confidence is None


def test_span_with_id_and_confidence() -> None:
    span = Span(
        start=0,
        end=8,
        text="John Doe",
        type="name",
        detector="ner:PERSON",
        id="p1",
        confidence=0.92,
    )
    assert span.id == "p1"
    assert span.confidence == pytest.approx(0.92)


def test_span_is_frozen() -> None:
    span = Span(start=0, end=1, text="x", type="name", detector="literal")
    with pytest.raises((AttributeError, TypeError)):
        span.start = 5  # type: ignore[misc]


def test_apply_spans_empty_returns_text_unchanged() -> None:
    text = "Hello world"
    result = apply_spans(text, [], lambda _span: "<TOKEN>")
    assert result == text


def test_apply_spans_non_overlapping_substitutions_preserve_offsets() -> None:
    text = "Hello John, this is Bob"
    spans = [
        Span(start=6, end=10, text="John", type="name", detector="literal"),
        Span(start=20, end=23, text="Bob", type="name", detector="literal"),
    ]
    result = apply_spans(text, spans, lambda _s: "<NAME>")
    assert result == "Hello <NAME>, this is <NAME>"


def test_apply_spans_overlap_literal_beats_ner() -> None:
    text = "John works at ACME"
    spans = [
        Span(start=14, end=18, text="ACME", type="org", detector="literal"),
        Span(start=14, end=18, text="ACME", type="org", detector="ner:ORG"),
    ]
    result = apply_spans(
        text,
        spans,
        lambda s: "<LITERAL>" if s.detector == "literal" else "<NER>",
    )
    assert result == "John works at <LITERAL>"


def test_apply_spans_overlap_length_tiebreak_longer_wins() -> None:
    text = "Acme Corporation Ltd"
    spans = [
        Span(start=0, end=4, text="Acme", type="name", detector="literal"),
        Span(
            start=0, end=16, text="Acme Corporation", type="org",
            detector="literal",
        ),
    ]
    result = apply_spans(text, spans, lambda s: f"<{s.type.upper()}>")
    assert result == "<ORG> Ltd"


def test_apply_spans_ignore_list_suppresses_matching_span() -> None:
    text = "John and Bob met"
    spans = [
        Span(start=0, end=4, text="John", type="name", detector="literal"),
        Span(start=9, end=12, text="Bob", type="name", detector="literal"),
    ]
    result = apply_spans(text, spans, lambda _s: "<NAME>", ignore=["bob"])
    assert result == "<NAME> and Bob met"


def test_apply_spans_ignore_uses_nfkc_casefold() -> None:
    text = "Visit Straße for details"
    spans = [
        Span(start=6, end=12, text="Straße", type="loc", detector="literal"),
    ]
    result = apply_spans(text, spans, lambda _s: "<LOC>", ignore=["strasse"])
    assert result == text


def test_apply_spans_overlap_structured_beats_ner() -> None:
    text = "Contact a@example.com today"
    spans = [
        Span(
            start=8, end=21, text="a@example.com", type="email",
            detector="structured:email",
        ),
        Span(
            start=8, end=21, text="a@example.com", type="email",
            detector="ner:EMAIL",
        ),
    ]
    result = apply_spans(
        text,
        spans,
        lambda s: "<STRUCT>" if s.detector.startswith("structured") else "<NER>",
    )
    assert result == "Contact <STRUCT> today"

