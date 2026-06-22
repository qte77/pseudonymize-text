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
from email.utils import formataddr, getaddresses
from pathlib import Path

_PSEUDO_HEADERS: frozenset[str] = frozenset(
    {"From", "To", "Cc", "Bcc", "Subject", "Reply-To"}
)
# Address headers must be rebuilt via getaddresses/formataddr: assigning a
# token like ``<NAME:hex>`` straight back under policy.default makes the RFC
# 5322 address parser treat the token's ``<`` as an angle-addr delimiter and
# mangle it (``<NAME>:hex>``). Subject is unstructured, so whole-value applies.
_ADDRESS_HEADERS: frozenset[str] = frozenset({"From", "To", "Cc", "Bcc", "Reply-To"})
_STRIP_HEADERS: frozenset[str] = frozenset(
    {"DKIM-Signature", "ARC-Seal", "ARC-Message-Signature", "ARC-Authentication-Results"}
)
_TEXT_TYPES: frozenset[str] = frozenset({"text/plain", "text/html"})


def _read_eml(src: Path) -> EmailMessage:
    """Parse ``src`` as an RFC 5322 message under ``policy.default``."""
    parser = BytesParser(policy=policy.default)
    with src.open("rb") as fh:
        msg = parser.parse(fh)
    if not isinstance(msg, EmailMessage):  # pragma: no cover - policy.default
        raise TypeError(f"expected EmailMessage, got {type(msg)!r}")
    return msg


def process_eml(
    src: Path, dst: Path, transform: Callable[[str, Path], str]
) -> None:
    """Read ``src`` as RFC 5322, rewrite per ADR_002, atomically write ``dst``."""
    msg = _read_eml(src)
    transform_message(msg, transform, Path(src.name))
    dst.write_bytes(bytes(msg))


def scan_eml(src: Path, transform: Callable[[str, Path], str]) -> None:
    """Detection-only: parse ``src`` and run ``transform`` per part; write nothing.

    Lets ``detect`` surface the same mail spans ``apply`` would substitute, so the
    audit plan is not silently empty for ``.eml`` inputs (the transform records
    spans and returns its text unchanged).
    """
    transform_message(_read_eml(src), transform, Path(src.name))


def transform_message(
    msg: EmailMessage,
    transform: Callable[[str, Path], str],
    rel: Path,
) -> None:
    """Apply the ADR_002 in-place mutations to an already-parsed message.

    Shared with ``formats.mbox.process_mbox`` so the per-message contract
    cannot drift between the two formats.
    """
    _strip_headers(msg)
    _pseudonymise_headers(msg, transform, rel)
    for part in msg.walk():
        if part.is_multipart():
            continue
        _rewrite_part(part, transform, rel)


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
        if header in _ADDRESS_HEADERS:
            new = _pseudonymise_addresses(str(value), transform, rel)
        else:
            new = transform(str(value), rel)
        del msg[header]
        msg[header] = new


def _pseudonymise_addresses(
    value: str, transform: Callable[[str, Path], str], rel: Path
) -> str:
    """Pseudonymise an address header without the RFC 5322 parser mangling tokens.

    Each address is split into ``(display-name, addr-spec)``; both are run
    through ``transform`` and recombined as a single quoted display name with no
    addr-spec, so the resulting ``<TYPE:hex>`` tokens survive re-serialization
    verbatim and the header still re-parses.
    """
    out: list[str] = []
    for display, addr in getaddresses([value]):
        tokens = [
            t
            for t in (
                transform(display, rel) if display else "",
                transform(addr, rel) if addr else "",
            )
            if t
        ]
        if tokens:
            out.append(formataddr((" ".join(tokens), "")))
    return ", ".join(out)


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
