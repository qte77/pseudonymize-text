import pytest
from pseudonymize_text.tokenize import hmac_token


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
