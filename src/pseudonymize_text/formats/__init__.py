"""Mail-format dispatch (.eml / .mbox) per ADR_002.

Public surface:
    is_mail_format(suffix) -> bool
    process_eml(src, dst, transform) -> None
    process_mbox(src, dst, transform) -> None  # fans out to dst/<seq>.eml
"""

from .eml import process_eml
from .mbox import process_mbox

__all__ = ["is_mail_format", "process_eml", "process_mbox"]

_MAIL_SUFFIXES: frozenset[str] = frozenset({".eml", ".mbox"})


def is_mail_format(suffix: str) -> bool:
    """Return True if ``suffix`` (incl. dot) is handled by this module."""
    return suffix in _MAIL_SUFFIXES
