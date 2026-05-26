"""Tests for cli.py (issue #13)."""

from pathlib import Path

import pytest

from pseudonymize_text.cli import main


def test_cli_no_args_exits_with_usage_error() -> None:
    assert main([]) == 2


def test_cli_unknown_subcommand_exits_with_usage_error() -> None:
    assert main(["totally-unknown"]) == 2


def test_cli_detect_without_in_dir_exits_with_usage_error() -> None:
    assert main(["detect"]) == 2


def test_cli_detect_missing_key_exits_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    monkeypatch.delenv("PSEUDONYMIZE_KEY", raising=False)
    assert main(["detect", str(in_dir), "--no-terms"]) == 3


def test_cli_apply_writes_substituted_output_and_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text(
        "Contact alice@acme.com soon", encoding="utf-8"
    )
    mapping = tmp_path / "mapping.json"
    report = tmp_path / "report.jsonl"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    rc = main(
        [
            "apply", str(in_dir), str(out_dir),
            "--no-terms",
            "--mapping", str(mapping),
            "--report", str(report),
        ]
    )

    assert rc == 0
    written = (out_dir / "a.txt").read_text(encoding="utf-8")
    assert "alice@acme.com" not in written
    assert "<EMAIL:" in written
    assert mapping.exists()
    assert "alice@acme.com" in mapping.read_text(encoding="utf-8")


def test_cli_detect_writes_report_with_header_and_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text(
        "Contact alice@acme.com about the order", encoding="utf-8"
    )
    report = tmp_path / "report.jsonl"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    rc = main(
        ["detect", str(in_dir), "--no-terms", "--report", str(report)]
    )

    assert rc == 0
    lines = report.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 2
    assert "pseudonymize.report/1" in lines[0]
    assert "alice@acme.com" in "\n".join(lines[1:])
