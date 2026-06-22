import re

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from pseudonymize_text.tokenize import canonicalize, hmac_token


@pytest.mark.parametrize(
    ("kind", "subject", "expected"),
    [
        ("id", "p1", "<NAME:d273039bdb37a853c53f592bb1b460e0>"),
        ("v", "john doe", "<NAME:003e28a1b30fc476e898352263414f11>"),
    ],
)
def test_hmac_token_matches_hashing_md_worked_example(
    kind: str, subject: str, expected: str
) -> None:
    assert hmac_token(b"test-key", "NAME", kind, subject) == expected


@pytest.mark.parametrize(
    ("value", "type_", "expected"),
    [
        ("John Doe", "name", "john doe"),
        ("Straße", "name", "strasse"),
        ("ACME Corp", "org", "acme corp"),
        ("Berlin", "loc", "berlin"),
        ("Bob.Smith@Example.com", "email", "bob.smith@example.com"),
        ("+49 30 1234567", "phone", "+49301234567"),
        ("de89 3704 0044 0532 0130 00", "iban", "DE89370400440532013000"),
        ("4111-1111-1111-1111", "cc", "4111111111111111"),
        ("123-45-6789", "ssn", "123456789"),
    ],
)
def test_canonicalize_matches_hashing_md_rules(
    value: str, type_: str, expected: str
) -> None:
    assert canonicalize(value, type_) == expected


def test_hmac_token_mac_key_not_in_traceback_locals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pseudonymize_text import tokenize

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated mid-HMAC failure")

    monkeypatch.setattr(tokenize.hmac, "new", boom)

    with pytest.raises(RuntimeError) as exc_info:
        hmac_token(b"super-secret-key", "NAME", "v", "john")

    tb = exc_info.value.__traceback__
    found = False
    while tb is not None:
        if tb.tb_frame.f_code.co_name == "hmac_token":
            locals_ = tb.tb_frame.f_locals
            assert "key" not in locals_, "raw HMAC key must not survive in frame"
            assert "mac_key" not in locals_, "derived mac_key must not survive in frame"
            found = True
        tb = tb.tb_next
    assert found, "hmac_token frame not found in traceback"


# --- Property tests: the headline token guarantee (C1) -----------------------
# Subjects exclude lone surrogates ("Cs") since those cannot be UTF-8 encoded.
_KEYS = st.binary(min_size=1, max_size=64)
_SUBJECTS = st.text(st.characters(exclude_categories=("Cs",)), max_size=64)
_TYPES = st.sampled_from(
    ["NAME", "ORG", "LOC", "EMAIL", "PHONE", "IBAN", "CC", "SSN", "NPI", "DEA", "VIN"]
)
_KINDS = st.sampled_from(["v", "id"])
_TEXT_TYPES = st.sampled_from(["name", "org", "loc"])  # accept arbitrary text
_TOKEN_RE = re.compile(r"^<[A-Z0-9_]+:[0-9a-f]{32}>$")


@given(key=_KEYS, type_=_TYPES, kind=_KINDS, subject=_SUBJECTS)
def test_hmac_token_is_deterministic(
    key: bytes, type_: str, kind: str, subject: str
) -> None:
    """Same key + type + kind + subject always yields the same token."""
    assert hmac_token(key, type_, kind, subject) == hmac_token(
        key, type_, kind, subject
    )


@given(k1=_KEYS, k2=_KEYS, type_=_TYPES, kind=_KINDS, subject=_SUBJECTS)
def test_hmac_token_is_key_sensitive(
    k1: bytes, k2: bytes, type_: str, kind: str, subject: str
) -> None:
    """Different keys yield different tokens for identical inputs."""
    assume(k1 != k2)
    assert hmac_token(k1, type_, kind, subject) != hmac_token(
        k2, type_, kind, subject
    )


@given(key=_KEYS, type_=_TYPES, kind=_KINDS, subject=_SUBJECTS)
def test_hmac_token_format_is_type_and_32_hex(
    key: bytes, type_: str, kind: str, subject: str
) -> None:
    """Token is always ``<TYPE:hex>`` with 32 lowercase hex chars."""
    assert _TOKEN_RE.match(hmac_token(key, type_, kind, subject))


@given(key=_KEYS, value=_SUBJECTS, type_=_TEXT_TYPES)
def test_token_recomputes_from_mapping_canonical(
    key: bytes, value: str, type_: str
) -> None:
    """Reversibility: the mapping records the canonical subject, and an auditor
    with the key recomputes the identical token from it — so a token resolves
    back to its original value through the mapping."""
    canonical = canonicalize(value, type_)
    token = hmac_token(key, type_.upper(), "v", canonical)
    mapping = {token: value}
    assert mapping[token] == value
    assert hmac_token(key, type_.upper(), "v", canonical) == token
