"""EU national-ID detectors (issue #86): DE / FR / GB / ES / IT.

Checksum-validated via ``python-stdnum``; jurisdiction-tagged **EU** per
ADR_003. Off by default — enable with ``--detectors eu``.

Naming: the type is the *identifier*, not the issuing agency. ``fr_nir`` is the
French social-security number (INSEE is the agency that issues it); ``gb_nhs``
is the NHS *number* (not the NHS organisation).
"""

import re
from collections.abc import Iterator

from stdnum.de import idnr as _de_idnr
from stdnum.es import dni as _es_dni
from stdnum.es import nie as _es_nie
from stdnum.fr import nir as _fr_nir
from stdnum.gb import nhs as _gb_nhs
from stdnum.it import codicefiscale as _it_cf

from ..replacer import Span

# Pre-filters; the stdnum checksum is the real gate (lookalikes are dropped).
_DE_STEUER_RE = re.compile(r"\b\d{11}\b")
_FR_NIR_RE = re.compile(r"\b[12]\d{14}\b")
_GB_NHS_RE = re.compile(r"\b\d{3}[ -]?\d{3}[ -]?\d{4}\b")
_ES_RE = re.compile(r"\b(?:[XYZ]\d{7}|\d{8})[A-Z]\b", re.IGNORECASE)
_IT_CF_RE = re.compile(
    r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b", re.IGNORECASE
)


def detect_de_steuer(text: str) -> Iterator[Span]:
    """Yield a ``Span`` per valid German Steuer-ID (11 digits)."""
    for m in _DE_STEUER_RE.finditer(text):
        if _de_idnr.is_valid(m.group(0)):
            yield Span(
                start=m.start(), end=m.end(), text=m.group(0),
                type="de_steuer", detector="eu:de_steuer",
            )


def detect_fr_nir(text: str) -> Iterator[Span]:
    """Yield a ``Span`` per valid French NIR (15 digits; the INSEE number)."""
    for m in _FR_NIR_RE.finditer(text):
        if _fr_nir.is_valid(m.group(0)):
            yield Span(
                start=m.start(), end=m.end(), text=m.group(0),
                type="fr_nir", detector="eu:fr_nir",
            )


def detect_gb_nhs(text: str) -> Iterator[Span]:
    """Yield a ``Span`` per valid UK NHS number (10 digits, optionally 3-3-4)."""
    for m in _GB_NHS_RE.finditer(text):
        if _gb_nhs.is_valid(m.group(0)):
            yield Span(
                start=m.start(), end=m.end(), text=m.group(0),
                type="gb_nhs", detector="eu:gb_nhs",
            )


def detect_es_dni(text: str) -> Iterator[Span]:
    """Yield a ``Span`` per valid Spanish DNI or NIE (both typed ``es_dni``)."""
    for m in _ES_RE.finditer(text):
        value = m.group(0)
        if _es_dni.is_valid(value) or _es_nie.is_valid(value):
            yield Span(
                start=m.start(), end=m.end(), text=value,
                type="es_dni", detector="eu:es_dni",
            )


def detect_it_cf(text: str) -> Iterator[Span]:
    """Yield a ``Span`` per valid Italian Codice Fiscale (16 chars)."""
    for m in _IT_CF_RE.finditer(text):
        if _it_cf.is_valid(m.group(0)):
            yield Span(
                start=m.start(), end=m.end(), text=m.group(0),
                type="it_cf", detector="eu:it_cf",
            )
