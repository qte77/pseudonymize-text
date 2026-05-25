"""Tests for the replacer module (issue #9)."""

import pytest

from pseudonymize_text.replacer import Span, apply_spans


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

