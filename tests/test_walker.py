"""Tests for the walker module (issue #10)."""

from pathlib import Path

from pseudonymize_text.walker import walk_and_process


def test_walker_whitelisted_text_file_transformed(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "hello.txt").write_text("hello world", encoding="utf-8")

    walk_and_process(in_dir, out_dir, lambda text, _path: text.upper())

    assert (out_dir / "hello.txt").read_text(encoding="utf-8") == "HELLO WORLD"


def test_walker_non_whitelisted_file_byte_copied(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    raw = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    (in_dir / "image.png").write_bytes(raw)

    walk_and_process(in_dir, out_dir, lambda text, _path: text.upper())

    assert (out_dir / "image.png").read_bytes() == raw
