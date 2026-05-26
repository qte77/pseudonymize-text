"""Tests for detectors/ner.py (issue #12).

The NER detector is gated behind the optional ``[ner]`` extra. Tests that
require ``spacy`` itself import-skip; tests that document the no-extra
fallback (clear ImportError with an install hint) run unconditionally.
"""

import sys

import pytest

from pseudonymize_text.detectors.ner import detect_ner


def test_detect_ner_raises_with_install_hint_when_spacy_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "spacy", None)
    with pytest.raises(ImportError, match=r"\[ner\]"):
        list(detect_ner("Alice met Bob in Paris"))


def test_detect_ner_label_mapping() -> None:
    pytest.importorskip("spacy")
    try:
        import spacy

        spacy.load("xx_ent_wiki_sm")
    except (OSError, ImportError):
        pytest.skip("xx_ent_wiki_sm model not installed")

    text = "Alice works at Acme Corporation in Paris."
    spans = list(detect_ner(text))

    types = {s.type for s in spans}
    assert types <= {"name", "org", "loc"}
    assert all(s.detector.startswith("ner:") for s in spans)


def test_detect_ner_stoplist_excludes() -> None:
    pytest.importorskip("spacy")
    try:
        import spacy

        spacy.load("xx_ent_wiki_sm")
    except (OSError, ImportError):
        pytest.skip("xx_ent_wiki_sm model not installed")

    text = "Alice met Bob in Paris."
    spans = list(detect_ner(text, stoplist=frozenset({"alice"})))
    assert all(s.text.lower() != "alice" for s in spans)
