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
