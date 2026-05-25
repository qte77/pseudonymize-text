"""HMAC-SHA256 token construction and per-type canonicalization (HASHING.md §1, §2)."""

import hashlib
import hmac
import re
import unicodedata

import phonenumbers


def canonicalize(value: str, type_: str) -> str:
    """Return canonical form of ``value`` for ``type_`` per HASHING.md §2."""
    if type_ in ("name", "org", "loc"):
        return unicodedata.normalize("NFKC", value).casefold()
    if type_ == "email":
        return unicodedata.normalize("NFKC", value).lower()
    if type_ == "phone":
        parsed = phonenumbers.parse(value, None)
        return f"+{parsed.country_code}{parsed.national_number}"
    if type_ == "iban":
        return re.sub(r"\s+", "", value).upper()
    if type_ in ("cc", "ssn"):
        return re.sub(r"\D", "", value)
    raise ValueError(f"unknown type: {type_}")


def hmac_token(key: bytes, type_: str, kind: str, subject: str) -> str:
    """Return the pseudonymization token for ``(kind, subject)`` under ``type_``.

    Implements HASHING.md §1:
    ``token = "<" + TYPE + ":" + hex(HMAC-SHA256(K, M)[:16]) + ">"``
    with ``K = key || ":" || lowercase(TYPE)`` and ``M = kind || ":" || subject``.

    Args:
        key: Secret HMAC key (raw bytes).
        type_: Uppercase entity type (e.g. ``"NAME"``).
        kind: ``"id"`` (subject is a group id string) or ``"v"`` (subject is
            the per-type canonical form of a value; see HASHING.md §2).
        subject: Group id or canonical value, depending on ``kind``.

    Returns:
        Token of the form ``<TYPE:hexdigits>`` with 32 lowercase hex chars
        (128-bit truncation of HMAC-SHA256).
    """
    mac_key = key + b":" + type_.lower().encode()
    del key
    try:
        mac_msg = (kind + ":" + subject).encode()
        mac = hmac.new(mac_key, mac_msg, hashlib.sha256).digest()
        token = f"<{type_}:{mac[:16].hex()}>"
    finally:
        del mac_key
    return token
