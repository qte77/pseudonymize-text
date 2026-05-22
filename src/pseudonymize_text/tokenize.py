"""HMAC-SHA256 token construction per HASHING.md §1."""

import hashlib
import hmac


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
    mac_msg = (kind + ":" + subject).encode()
    mac = hmac.new(mac_key, mac_msg, hashlib.sha256).digest()
    return f"<{type_}:{mac[:16].hex()}>"
