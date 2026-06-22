"""EU national-ID detector tests (issue #86): DE/FR/GB/ES/IT.

Fixtures are checksum-valid example numbers verified against python-stdnum;
the paired "bad" values fail the respective checksum.
"""

from collections.abc import Iterable

from pseudonymize_text.detectors.eu_ids import (
    detect_de_steuer,
    detect_es_dni,
    detect_fr_nir,
    detect_gb_nhs,
    detect_it_cf,
)
from pseudonymize_text.replacer import Span


def _texts(spans: Iterable[Span]) -> set[str]:
    return {s.text for s in spans}


def test_de_steuer_valid_detected_invalid_rejected() -> None:
    found = _texts(detect_de_steuer("Steuer-ID 36574261809; bad 36574261800."))
    assert "36574261809" in found
    assert "36574261800" not in found


def test_de_steuer_span_tags() -> None:
    (s,) = list(detect_de_steuer("36574261809"))
    assert (s.type, s.detector) == ("de_steuer", "eu:de_steuer")


def test_fr_nir_valid_detected_invalid_rejected() -> None:
    found = _texts(detect_fr_nir("NIR 180057511902494; bad 295109912611174."))
    assert "180057511902494" in found
    assert "295109912611174" not in found


def test_gb_nhs_plain_and_grouped_detected() -> None:
    assert "9434765919" in _texts(detect_gb_nhs("NHS no 9434765919"))
    assert "943 476 5919" in _texts(detect_gb_nhs("NHS no 943 476 5919"))


def test_gb_nhs_invalid_rejected() -> None:
    assert "9434765910" not in _texts(detect_gb_nhs("NHS 9434765910"))


def test_es_dni_and_nie_detected() -> None:
    assert "54362315K" in _texts(detect_es_dni("DNI 54362315K"))
    assert "X2482300W" in _texts(detect_es_dni("NIE X2482300W"))


def test_es_dni_invalid_letter_rejected() -> None:
    assert _texts(detect_es_dni("DNI 54362315A")) == set()


def test_es_dni_span_type_is_es_dni_for_both() -> None:
    (s,) = list(detect_es_dni("X2482300W"))
    assert (s.type, s.detector) == ("es_dni", "eu:es_dni")


def test_it_cf_valid_detected_invalid_rejected() -> None:
    found = _texts(detect_it_cf("CF RCCMNL83S18D969H; bad RCCMNL83S18D969A."))
    assert "RCCMNL83S18D969H" in found
    assert "RCCMNL83S18D969A" not in found


def test_it_cf_case_insensitive() -> None:
    assert "rccmnl83s18d969h" in _texts(detect_it_cf("cf rccmnl83s18d969h"))
