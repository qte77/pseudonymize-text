"""Structured-ID detectors: email / phone / IBAN / credit-card / SSN.

All canonicalisation happens in-tree (``tokenize.canonicalize``) per
HASHING.md §8 — these detectors only validate that a candidate is real
(mod-97 / Luhn / phonenumbers.is_valid_number) and emit a ``Span`` over
the original surface text. The token derivation reads ``Span.text`` and
applies the per-type canonical form at hashing time.
"""

import re
from collections.abc import Iterator

import phonenumbers
from stdnum import iban
from stdnum.luhn import is_valid as luhn_is_valid

from ..replacer import Span

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_IBAN_CANDIDATE_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_CC_CANDIDATE_RE = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def detect_emails(text: str) -> Iterator[Span]:
    """Yield a ``Span`` for every RFC-ish email address."""
    for m in _EMAIL_RE.finditer(text):
        yield Span(
            start=m.start(),
            end=m.end(),
            text=m.group(0),
            type="email",
            detector="structured:email",
        )


def detect_phones(text: str, *, default_region: str | None = None) -> Iterator[Span]:
    """Yield a ``Span`` for every ``phonenumbers``-valid number in ``text``."""
    for match in phonenumbers.PhoneNumberMatcher(text, default_region):
        yield Span(
            start=match.start,
            end=match.end,
            text=match.raw_string,
            type="phone",
            detector="structured:phone",
        )


def detect_ibans(text: str) -> Iterator[Span]:
    """Yield a ``Span`` for every mod-97-valid IBAN candidate."""
    for m in _IBAN_CANDIDATE_RE.finditer(text):
        candidate = m.group(0)
        if iban.is_valid(candidate):
            yield Span(
                start=m.start(),
                end=m.end(),
                text=candidate,
                type="iban",
                detector="structured:iban",
            )


def detect_credit_cards(text: str) -> Iterator[Span]:
    """Yield a ``Span`` for every Luhn-valid credit-card-shaped number."""
    for m in _CC_CANDIDATE_RE.finditer(text):
        candidate = m.group(0)
        digits = re.sub(r"\D", "", candidate)
        if luhn_is_valid(digits):
            yield Span(
                start=m.start(),
                end=m.end(),
                text=candidate,
                type="cc",
                detector="structured:cc",
            )


def detect_ssns(text: str) -> Iterator[Span]:
    """Yield a ``Span`` for every US-format ``NNN-NN-NNNN`` SSN."""
    for m in _SSN_RE.finditer(text):
        yield Span(
            start=m.start(),
            end=m.end(),
            text=m.group(0),
            type="ssn",
            detector="structured:ssn",
        )
