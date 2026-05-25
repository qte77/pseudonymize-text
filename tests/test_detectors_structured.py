"""Tests for detectors/structured.py (issue #11)."""

import pytest
from pseudonymize_text.detectors.structured import (
    detect_credit_cards,
    detect_emails,
    detect_ibans,
    detect_phones,
    detect_ssns,
)


def test_detect_emails_basic() -> None:
    text = "contact alice@example.com or bob.smith+tag@sub.acme.co.uk today"
    spans = list(detect_emails(text))

    assert [s.text for s in spans] == [
        "alice@example.com",
        "bob.smith+tag@sub.acme.co.uk",
    ]
    assert all(s.type == "email" for s in spans)
    assert all(s.detector == "structured:email" for s in spans)


def test_detect_emails_ignores_lookalikes() -> None:
    text = "no@ here, @starts, dangling@, plain.user"
    assert list(detect_emails(text)) == []


def test_detect_phones_e164_acceptable() -> None:
    pytest.importorskip("phonenumbers")
    text = "Call +49 30 12345678 or 030 12345678 (DE) tomorrow"
    spans = list(detect_phones(text, default_region="DE"))
    assert any("12345678" in s.text for s in spans)
    assert all(s.detector == "structured:phone" for s in spans)


def test_detect_ibans_validates_mod97() -> None:
    pytest.importorskip("stdnum")
    text = "Wire to DE89370400440532013000 (valid) or DE89370400440532013001 (invalid)"
    spans = list(detect_ibans(text))
    assert [s.text for s in spans] == ["DE89370400440532013000"]
    assert all(s.detector == "structured:iban" for s in spans)


def test_detect_credit_cards_luhn_validated() -> None:
    pytest.importorskip("stdnum")
    text = "Card 4111-1111-1111-1111 (valid Luhn), bogus 4111-1111-1111-1112"
    spans = list(detect_credit_cards(text))
    assert [s.text for s in spans] == ["4111-1111-1111-1111"]
    assert all(s.detector == "structured:cc" for s in spans)


def test_detect_ssns_us_format() -> None:
    text = "SSN 123-45-6789 reported; bad: 12-34-5678 or 1234567890"
    spans = list(detect_ssns(text))
    assert [s.text for s in spans] == ["123-45-6789"]
    assert all(s.detector == "structured:ssn" for s in spans)
