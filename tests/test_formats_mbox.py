"""Tests for .mbox fan-out (issue #10 follow-up, ADR_002)."""

import mailbox
from email.message import EmailMessage
from pathlib import Path

from pseudonymize_text.walker import walk_and_process


def _build_message(to: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = "Alice <alice@example.com>"
    msg["To"] = to
    msg["Subject"] = "hi"
    msg.set_content(body)
    return msg


def test_walker_mbox_fan_out_to_per_message_eml(tmp_path: Path) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    mbox_path = in_dir / "inbox.mbox"
    box = mailbox.mbox(str(mbox_path), create=True)
    box.add(_build_message("Bob <bob@example.com>", "Hello bob@example.com"))
    box.add(_build_message("Carol <carol@example.com>", "Hi carol@example.com"))
    box.close()

    def transform(text: str, _rel: Path) -> str:
        return text.replace("bob@example.com", "<EMAIL:b>").replace(
            "carol@example.com", "<EMAIL:c>"
        )

    walk_and_process(in_dir, out_dir, transform)

    # mbox should fan out to out_dir/inbox/0000.eml + 0001.eml (per ADR_002).
    eml_dir = out_dir / "inbox"
    assert eml_dir.is_dir(), f"expected fan-out dir at {eml_dir}"
    eml_files = sorted(eml_dir.glob("*.eml"))
    assert len(eml_files) == 2

    first = eml_files[0].read_text(encoding="utf-8")
    second = eml_files[1].read_text(encoding="utf-8")
    # Body emails pseudonymised
    assert "<EMAIL:b>" in first
    assert "<EMAIL:c>" in second
    # Header emails pseudonymised (To: line gets the transform too)
    assert "bob@example.com" not in first
    assert "carol@example.com" not in second
    # The single .mbox file itself must NOT appear in out_dir
    assert not (out_dir / "inbox.mbox").exists()
