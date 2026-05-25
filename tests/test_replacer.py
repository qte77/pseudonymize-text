"""Tests for the replacer module (issue #9)."""

import pytest
from pseudonymize_text.replacer import Span


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
