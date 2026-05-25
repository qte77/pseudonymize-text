"""Mail-format dispatch (.eml / .mbox) per ADR_002.

Public surface:
    is_mail_format(suffix) -> bool
    process_eml(src, dst, transform) -> None
"""

from .eml import process_eml

__all__ = ["is_mail_format", "process_eml"]

_MAIL_SUFFIXES: frozenset[str] = frozenset({".eml"})


def is_mail_format(suffix: str) -> bool:
    """Return True if ``suffix`` (incl. dot) is handled by this module.

    `.mbox` fan-out is planned for a follow-up; this PR ships `.eml` only.
    """
    return suffix in _MAIL_SUFFIXES
