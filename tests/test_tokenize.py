import pytest

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
