"""Tests for detectors/terms.py (issue #7)."""

from pathlib import Path

import pytest

from pseudonymize_text.detectors.terms import TermRow, load_terms


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
