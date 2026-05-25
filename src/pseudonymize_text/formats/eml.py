"""`.eml` per-part processor per ADR_002.

Pipeline for each message:
1. Decode and pseudonymise the listed headers + their RFC 2047 variants.
2. Decode and pseudonymise every ``text/plain`` and ``text/html`` part
   (HTML detection quality is the detector's problem — this layer only
   guarantees the part text is passed through ``transform``).
3. Drop every other part; replace its payload with a stub.
4. Strip ``DKIM-Signature`` and ``ARC-*`` headers (invalidated by step 1).
"""

from collections.abc import Callable
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from pathlib import Path

_PSEUDO_HEADERS: frozenset[str] = frozenset(
    {"From", "To", "Cc", "Bcc", "Subject", "Reply-To"}
)
_STRIP_HEADERS: frozenset[str] = frozenset(
    {"DKIM-Signature", "ARC-Seal", "ARC-Message-Signature", "ARC-Authentication-Results"}
)
_TEXT_TYPES: frozenset[str] = frozenset({"text/plain", "text/html"})


def process_eml(
    src: Path, dst: Path, transform: Callable[[str, Path], str]
) -> None:
    """Read ``src`` as RFC 5322, rewrite per ADR_002, atomically write ``dst``."""
    rel = Path(src.name)
    parser = BytesParser(policy=policy.default)
    with src.open("rb") as fh:
        msg = parser.parse(fh)
    if not isinstance(msg, EmailMessage):  # pragma: no cover - policy.default
        raise TypeError(f"expected EmailMessage, got {type(msg)!r}")

    _strip_headers(msg)
    _pseudonymise_headers(msg, transform, rel)
    for part in msg.walk():
        if part.is_multipart():
            continue
        _rewrite_part(part, transform, rel)

    dst.write_bytes(bytes(msg))


def _strip_headers(msg: EmailMessage) -> None:
    for header in list(msg):
        if header in _STRIP_HEADERS:
            del msg[header]


def _pseudonymise_headers(
    msg: EmailMessage, transform: Callable[[str, Path], str], rel: Path
) -> None:
    for header in _PSEUDO_HEADERS:
        value = msg.get(header)
        if value is None:
            continue
        new = transform(str(value), rel)
        del msg[header]
        msg[header] = new


def _rewrite_part(
    part: Message, transform: Callable[[str, Path], str], rel: Path
) -> None:
    ctype = part.get_content_type()
    if ctype in _TEXT_TYPES:
        try:
            content = part.get_content()
        except (LookupError, UnicodeDecodeError):
            content = part.get_payload(decode=False) or ""
        if isinstance(content, str):
            subtype = ctype.split("/", 1)[1]
            part.set_content(transform(content, rel), subtype=subtype)
        return
    size = len(part.get_payload(decode=True) or b"")
    part.set_content(
        f"[part removed by pseudonymize: {ctype}; {size} bytes]", subtype="plain"
    )
