"""`.mbox` fan-out processor per ADR_002.

One mbox file in `<in_dir>` becomes one sub-directory in `<out_dir>`
holding one `.eml` per message. The single-message rewrite shares
``formats.eml.transform_message`` so behaviour cannot drift.

Mbox dialect: stdlib ``mailbox.mbox`` (mboxo). We do not write mboxrd-
style `>From` quoting or `Content-Length` headers because we don't
re-assemble an mbox on the way out — the fan-out replaces it.
"""

import mailbox
from collections.abc import Callable, Iterator
from email.message import EmailMessage
from pathlib import Path

from .eml import transform_message


def process_mbox(
    src: Path, dst: Path, transform: Callable[[str, Path], str]
) -> None:
    """Fan ``src`` out into ``dst.with_suffix("")/<seq>.eml`` per ADR_002."""
    out_dir = dst.with_suffix("")
    out_dir.mkdir(parents=True, exist_ok=True)
    for rel, msg in _iter_messages(src):
        transform_message(msg, transform, rel)
        (out_dir / rel.name).write_bytes(bytes(msg))


def scan_mbox(src: Path, transform: Callable[[str, Path], str]) -> None:
    """Detection-only counterpart to ``process_mbox``.

    Runs ``transform`` per message without writing, so ``detect`` surfaces
    ``.mbox`` spans too.
    """
    for rel, msg in _iter_messages(src):
        transform_message(msg, transform, rel)


def _iter_messages(src: Path) -> Iterator[tuple[Path, EmailMessage]]:
    """Yield ``(<seq>.eml path, EmailMessage)`` for each message in ``src``."""
    box = mailbox.mbox(str(src), create=False)
    try:
        for i, msg in enumerate(box):
            if not isinstance(msg, EmailMessage):
                msg = _to_email_message(msg)
            yield Path(f"{i:04d}.eml"), msg
    finally:
        box.close()


def _to_email_message(msg: mailbox.mboxMessage) -> EmailMessage:
    """Re-parse a ``mailbox.mboxMessage`` under ``policy.default``.

    ``mailbox.mbox`` returns ``mboxMessage`` instances under the legacy
    ``compat32`` policy; ``transform_message`` and the modern ``get_content``
    API expect ``EmailMessage`` under ``policy.default``. Re-parse via
    bytes round-trip rather than fighting policy adapters.
    """
    from email import policy
    from email.parser import BytesParser

    reparsed = BytesParser(policy=policy.default).parsebytes(bytes(msg))
    if not isinstance(reparsed, EmailMessage):  # pragma: no cover
        raise TypeError(f"expected EmailMessage, got {type(reparsed)!r}")
    return reparsed
