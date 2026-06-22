"""PHI structured-ID detectors: NPI / DEA / VIN (issue #42).

Checksum-validated, dependency-light (reuses ``stdnum.luhn`` for NPI; DEA and
VIN checksums are hand-rolled — neither is in python-stdnum 2.2). Off by
default; enable with ``--detectors phi``. MRN has no checksum, so contextual
MRN detection (``detect_mrn``) is opt-in via ``--phi-context``. Clinical-NER
detection is deferred (it needs a gated model).
"""

import re
from collections.abc import Iterator

from stdnum.luhn import is_valid as luhn_is_valid

from ..replacer import Span

# NPI: 10 digits, Luhn-valid over the "80840" prefix + the 9-digit identifier
# (the 10th digit is the Luhn check). See CMS NPI check-digit spec.
_NPI_RE = re.compile(r"\b\d{10}\b")
# DEA registration number — the US medical controlled-substance prescriber ID
# (not the DEA agency): 2 letters (registrant type + last-name initial) + 7 digits.
_DEA_RE = re.compile(r"\b[A-Za-z]{2}\d{7}\b")
# VIN: 17 chars from the VIN alphabet (I, O, Q excluded).
_VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")

_VIN_TRANSLIT: dict[str, int] = {
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
}
_VIN_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)


def detect_npi(text: str) -> Iterator[Span]:
    """Yield a ``Span`` for every Luhn-valid NPI (10 digits)."""
    for m in _NPI_RE.finditer(text):
        if luhn_is_valid("80840" + m.group(0)):
            yield Span(
                start=m.start(), end=m.end(), text=m.group(0),
                type="npi", detector="phi:npi",
            )


def _dea_checksum_ok(value: str) -> bool:
    d = [int(c) for c in value[2:]]
    return (d[0] + d[2] + d[4] + 2 * (d[1] + d[3] + d[5])) % 10 == d[6]


def detect_dea(text: str) -> Iterator[Span]:
    """Yield a ``Span`` per checksum-valid DEA registration number.

    The DEA *number* is the US medical controlled-substance prescriber ID
    (not the Drug Enforcement Administration agency).
    """
    for m in _DEA_RE.finditer(text):
        if _dea_checksum_ok(m.group(0)):
            yield Span(
                start=m.start(), end=m.end(), text=m.group(0),
                type="dea", detector="phi:dea",
            )


def _vin_checksum_ok(vin: str) -> bool:
    total = 0
    for ch, weight in zip(vin, _VIN_WEIGHTS, strict=True):
        value = int(ch) if ch.isdigit() else _VIN_TRANSLIT.get(ch)
        if value is None:
            return False
        total += value * weight
    remainder = total % 11
    expected = "X" if remainder == 10 else str(remainder)
    return vin[8] == expected


def detect_vin(text: str) -> Iterator[Span]:
    """Yield a ``Span`` for every check-digit-valid VIN (17 chars)."""
    for m in _VIN_RE.finditer(text):
        if _vin_checksum_ok(m.group(0)):
            yield Span(
                start=m.start(), end=m.end(), text=m.group(0),
                type="vin", detector="phi:vin",
            )


# MRN: a 6-10 digit run gated on a nearby cue word. Medical record numbers have
# no checksum, so this is noisier than the types above — opt in via
# `--phi-context`. The cue must fall within `_MRN_CONTEXT_WINDOW` chars.
_MRN_RE = re.compile(r"\b\d{6,10}\b")
_MRN_CUE_RE = re.compile(
    r"\bmrn\b"
    r"|\bmedical\s+record(?:\s+(?:number|no\.?|#))?"
    r"|\brecord\s+(?:number|no\.?|#)"
    r"|\bmr\s*#"
    r"|\brec\s*#",
    re.IGNORECASE,
)
_MRN_CONTEXT_WINDOW = 60


def detect_mrn(text: str, window: int = _MRN_CONTEXT_WINDOW) -> Iterator[Span]:
    """Yield a ``Span`` per cued 6-10 digit MRN within ``window`` chars.

    The cue word (``MRN``, ``Medical Record Number``, ``Rec #`` …) must fall
    within ``window`` chars of the digit run. MRNs carry no checksum, so
    detection is context-gated and higher false-positive than NPI/DEA/VIN —
    review the report. Opt-in via ``--phi-context``.
    """
    cues = [(m.start(), m.end()) for m in _MRN_CUE_RE.finditer(text)]
    if not cues:
        return
    for m in _MRN_RE.finditer(text):
        n_start, n_end = m.start(), m.end()
        if any(
            max(n_start - c_end, c_start - n_end) <= window
            for c_start, c_end in cues
        ):
            yield Span(
                start=n_start, end=n_end, text=m.group(0),
                type="mrn", detector="phi:mrn",
            )
