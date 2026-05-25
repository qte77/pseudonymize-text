"""Tests for detectors/terms.py (issue #7)."""

from pathlib import Path

import pytest

from pseudonymize_text.detectors.terms import TermRow, detect_terms, load_terms


def test_load_terms_csv_required_value_only(tmp_path: Path) -> None:
    csv = tmp_path / "terms.csv"
    csv.write_text("value\nJohn Doe\n", encoding="utf-8")

    rows = load_terms(csv)

    assert rows == [TermRow(value="John Doe", type="name", id=None)]


def test_load_terms_csv_with_type_and_id(tmp_path: Path) -> None:
    csv = tmp_path / "terms.csv"
    csv.write_text(
        "id,value,type\np1,John Doe,name\np1,J. Doe,name\n,acme.com,org\n",
        encoding="utf-8",
    )

    rows = load_terms(csv)

    assert rows == [
        TermRow(value="John Doe", type="name", id="p1"),
        TermRow(value="J. Doe", type="name", id="p1"),
        TermRow(value="acme.com", type="org", id=None),
    ]


def test_load_terms_empty_file_returns_empty(tmp_path: Path) -> None:
    csv = tmp_path / "terms.csv"
    csv.write_text("", encoding="utf-8")
    assert load_terms(csv) == []


def test_load_terms_unknown_extension_raises(tmp_path: Path) -> None:
    f = tmp_path / "terms.xyz"
    f.write_text("anything", encoding="utf-8")
    with pytest.raises(ValueError, match="terms format"):
        load_terms(f)


def test_detect_terms_literal_word_boundary() -> None:
    text = "Met John Doe at the conference; johnson came later."
    terms = [TermRow(value="John Doe", type="name")]

    spans = list(detect_terms(text, terms))

    assert len(spans) == 1
    assert spans[0].start == 4
    assert spans[0].end == 12
    assert spans[0].text == "John Doe"
    assert spans[0].type == "name"
    assert spans[0].detector == "literal"
    assert spans[0].id is None


def test_detect_terms_literal_case_insensitive() -> None:
    text = "Alice met ALICE and alice"
    terms = [TermRow(value="alice", type="name")]

    spans = list(detect_terms(text, terms))

    assert [s.start for s in spans] == [0, 10, 20]


def test_detect_terms_wildcard_email_type() -> None:
    text = "Contact alice@acme.com or bob@acme.com today"
    terms = [TermRow(value="*@acme.com", type="email")]

    spans = list(detect_terms(text, terms))

    assert [s.text for s in spans] == ["alice@acme.com", "bob@acme.com"]
    assert all(s.detector == "pattern" for s in spans)
    assert all(s.type == "email" for s in spans)


def test_detect_terms_wildcard_name_type_respects_delimiter() -> None:
    text = "John Smith met Jane Smith at the office"
    terms = [TermRow(value="* Smith", type="name")]

    spans = list(detect_terms(text, terms))

    # `*` for name type matches non-whitespace/comma/semicolon, so it
    # captures just the immediately preceding word, not the whole phrase.
    assert sorted(s.text for s in spans) == ["Jane Smith", "John Smith"]


def test_detect_terms_id_propagates_to_span() -> None:
    text = "John, Doe John, J. Doe"
    terms = [
        TermRow(value="John", type="name", id="p1"),
        TermRow(value="Doe John", type="name", id="p1"),
        TermRow(value="J. Doe", type="name", id="p1"),
    ]

    spans = list(detect_terms(text, terms))

    # 3 matches; id="p1" on each.
    assert {s.id for s in spans} == {"p1"}


def test_load_terms_json_matches_csv_semantics(tmp_path: Path) -> None:
    j = tmp_path / "terms.json"
    j.write_text(
        '[{"id":"p1","value":"John Doe","type":"name"},'
        '{"value":"*@acme.com","type":"email"}]',
        encoding="utf-8",
    )

    rows = load_terms(j)

    assert rows == [
        TermRow(value="John Doe", type="name", id="p1"),
        TermRow(value="*@acme.com", type="email", id=None),
    ]
