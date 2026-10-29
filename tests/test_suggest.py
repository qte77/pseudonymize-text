"""Tests for suggest.py + `pseudonymize suggest-terms` (issue #106).

NER itself is stubbed: the spaCy model is not installed in CI, and the
behaviour under test is aggregation, not entity recognition.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from pseudonymize_text.cli import main
from pseudonymize_text.detectors.terms import TermRow, load_terms
from pseudonymize_text.replacer import Span
from pseudonymize_text.suggest import Candidate, format_candidates_csv, suggest_terms


def _ner(text: str, type_: str = "name") -> Span:
    return Span(start=0, end=len(text), text=text, type=type_, detector="ner:PERSON")


def test_suggest_terms_dedupes_case_insensitively_and_ranks_by_count() -> None:
    spans = [
        _ner("Carol"),
        _ner("Acme Ltd", "org"),
        _ner("carol"),
        _ner("Carol"),
        _ner("Acme  Ltd", "org"),
        _ner("Bob"),
    ]
    assert suggest_terms(spans, []) == [
        Candidate(value="Carol", type="name", count=3),
        Candidate(value="Acme Ltd", type="org", count=2),
        Candidate(value="Bob", type="name", count=1),
    ]


def test_suggest_terms_same_text_different_type_stays_separate() -> None:
    spans = [_ner("Jordan", "name"), _ner("Jordan", "loc")]
    assert {(c.value, c.type) for c in suggest_terms(spans, [])} == {
        ("Jordan", "name"),
        ("Jordan", "loc"),
    }


def test_suggest_terms_skips_values_already_covered_by_terms() -> None:
    terms = [TermRow(value="Carol Danvers"), TermRow(value="*Corp", type="org")]
    spans = [_ner("carol danvers"), _ner("Carol"), _ner("AcmeCorp", "org")]
    assert suggest_terms(spans, terms) == [Candidate(value="Carol", type="name", count=1)]


def test_format_candidates_csv_loads_as_a_term_list(tmp_path: Path) -> None:
    csv_text = format_candidates_csv(
        [Candidate(value="Carol", type="name", count=3), Candidate("Acme, Ltd", "org", 1)]
    )
    assert csv_text.splitlines()[0] == "value,type,id,count"
    path = tmp_path / "candidates.csv"
    path.write_text(csv_text, encoding="utf-8")
    assert load_terms(path) == [
        TermRow(value="Carol", type="name"),
        TermRow(value="Acme, Ltd", type="org"),
    ]


def _stub_ner(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(text: str, **_: object) -> Iterator[Span]:
        for name in ("Carol", "Acme Ltd"):
            start = text.find(name)
            if start >= 0:
                type_ = "org" if name.startswith("Acme") else "name"
                yield Span(start, start + len(name), name, type_, "ner:X")

    monkeypatch.setattr("pseudonymize_text.detectors.ner.detect_ner", fake)


def test_cli_suggest_terms_writes_candidates_without_key_or_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_ner(monkeypatch)
    monkeypatch.delenv("PSEUDONYMIZE_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text("Hi Carol, from Acme Ltd.", encoding="utf-8")
    (in_dir / "b.md").write_text("Carol again", encoding="utf-8")
    terms = tmp_path / "terms.csv"
    terms.write_text("value,type\nAcme Ltd,org\n", encoding="utf-8")
    out = tmp_path / "candidates.csv"

    rc = main(["suggest-terms", str(in_dir), "--terms", str(terms), "--out", str(out)])

    assert rc == 0
    assert out.read_text(encoding="utf-8").splitlines() == [
        "value,type,id,count",
        "Carol,name,,2",
    ]
    assert not (tmp_path / "runs").exists()


def test_cli_suggest_terms_prints_to_stdout_without_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stub_ner(monkeypatch)
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text("Carol at Acme Ltd", encoding="utf-8")

    assert main(["suggest-terms", str(in_dir)]) == 0
    assert capsys.readouterr().out.splitlines()[1:] == ["Acme Ltd,org,,1", "Carol,name,,1"]
