"""Tests for the walker module (issue #10)."""

import os
from pathlib import Path

import pytest

from pseudonymize_text.walker import SymlinkEscapeError, walk_and_process


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


def test_walker_file_symlink_escape_raises(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (in_dir / "escape.txt").symlink_to(outside)

    with pytest.raises(SymlinkEscapeError):
        walk_and_process(in_dir, out_dir, lambda text, _p: text)

    assert not (out_dir / "escape.txt").exists()


def test_walker_dir_symlink_not_followed(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "kept.txt").write_text("keep me", encoding="utf-8")

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    (in_dir / "link").symlink_to(outside, target_is_directory=True)

    walk_and_process(in_dir, out_dir, lambda text, _p: text)

    assert (out_dir / "kept.txt").exists()
    assert not (out_dir / "link" / "secret.txt").exists()
    assert not (out_dir / "link").exists()


def _build_multipart_eml() -> bytes:
    """RFC 5322 multipart: text/plain + DKIM header + binary attachment."""
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["From"] = "Alice <alice@example.com>"
    msg["To"] = "Bob <bob@example.com>"
    msg["Subject"] = "hello"
    msg["DKIM-Signature"] = "v=1; a=rsa-sha256; d=example.com; s=mail; b=fake"
    msg.set_content("plaintext body about alice@example.com")
    msg.add_attachment(
        b"\x89PNG\r\n\x1a\n", maintype="image", subtype="png", filename="x.png",
    )
    return bytes(msg)


def test_walker_eml_text_pseudonymized_binary_dropped_dkim_stripped(
    tmp_path: Path,
) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "msg.eml").write_bytes(_build_multipart_eml())

    walk_and_process(
        in_dir, out_dir, lambda text, _p: text.replace("alice@example.com", "<EMAIL>"),
    )

    out_bytes = (out_dir / "msg.eml").read_bytes()
    out_text = out_bytes.decode("utf-8", errors="replace")

    assert "<EMAIL>" in out_text
    assert "alice@example.com" not in out_text
    assert "DKIM-Signature" not in out_text
    assert b"\x89PNG" not in out_bytes
    assert "part removed by pseudonymize" in out_text


def test_walker_atomic_write_tmp_file_mode_is_0600(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text("hello", encoding="utf-8")
    captured: list[int] = []
    real_replace = os.replace

    def capture_then_replace(
        src: str | os.PathLike[str], dst: str | os.PathLike[str]
    ) -> None:
        captured.append(Path(src).stat().st_mode & 0o777)
        real_replace(src, dst)

    monkeypatch.setattr("os.replace", capture_then_replace)

    walk_and_process(in_dir, out_dir, lambda text, _path: text)

    assert captured == [0o600]
