"""End-to-end smoke tests against tests/fixtures/ (issue #14).

Runs ``pseudonymize`` against a small canonical corpus and asserts the
shape of the output, not byte-identity (golden output is sensitive to
HMAC key + tool version). For a byte-identical contract test, see the
forthcoming ``apply --plan`` rehydration once #13 lands the
remaining flags.
"""

import json
import shutil
from pathlib import Path

import pytest

from pseudonymize_text.cli import main

_FIXTURES = Path(__file__).parent / "fixtures"
_TEST_KEY = "ab" * 32


def _copy_corpus(dst: Path) -> None:
    shutil.copytree(_FIXTURES / "corpus", dst)


def test_e2e_detect_finds_terms_and_structured_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    _copy_corpus(in_dir)
    report = tmp_path / "report.jsonl"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", _TEST_KEY)

    rc = main(
        [
            "detect", str(in_dir),
            "--terms", str(_FIXTURES / "terms.csv"),
            "--report", str(report),
        ]
    )

    assert rc == 0
    lines = report.read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    records = [json.loads(line) for line in lines[1:]]

    assert header["schema"] == "pseudonymize.report/1"
    assert header["tool_version"]
    assert len(header["config_hash"]) == 32

    detectors_seen = {r["detector"] for r in records}
    assert "literal" in detectors_seen, "John Doe term should match literal"
    assert "structured:email" in detectors_seen
    assert "structured:phone" in detectors_seen
    assert "structured:iban" in detectors_seen
    assert "structured:cc" in detectors_seen
    assert "structured:ssn" in detectors_seen


def test_e2e_apply_substitutes_and_writes_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    _copy_corpus(in_dir)
    out_dir = tmp_path / "out"
    mapping = tmp_path / "mapping.json"
    report = tmp_path / "report.jsonl"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", _TEST_KEY)

    rc = main(
        [
            "apply", str(in_dir), str(out_dir),
            "--terms", str(_FIXTURES / "terms.csv"),
            "--mapping", str(mapping),
            "--report", str(report),
        ]
    )

    assert rc == 0
    written = (out_dir / "sample.txt").read_text(encoding="utf-8")
    # Every PII surface form is gone, replaced by <TYPE:hex> tokens
    for plaintext in (
        "John Doe",
        "j. doe",  # case-insensitive match
        "john.doe@acme.com",
        "123-45-6789",
        "4111-1111-1111-1111",
        "DE89370400440532013000",
    ):
        assert plaintext.lower() not in written.lower(), (
            f"{plaintext!r} should be substituted in out_dir/sample.txt"
        )
    assert "<NAME:" in written
    assert "<EMAIL:" in written
    assert "<SSN:" in written

    # Mapping retains the original plaintext for reverse lookup
    mapping_text = mapping.read_text(encoding="utf-8")
    assert "John Doe" in mapping_text
    assert "john.doe@acme.com" in mapping_text
