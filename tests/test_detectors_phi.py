"""PHI detector tests (issue #42): NPI / DEA / VIN checksum validation."""

from collections.abc import Iterable

from pseudonymize_text.detectors.phi import detect_dea, detect_npi, detect_vin
from pseudonymize_text.replacer import Span


def _texts(spans: Iterable[Span]) -> set[str]:
    return {s.text for s in spans}


def test_detect_npi_accepts_valid_rejects_bad_checksum() -> None:
    # 1234567893 is the canonical Luhn-valid NPI; 1234567890 fails the check.
    found = _texts(detect_npi("Provider NPI 1234567893; bad 1234567890."))
    assert "1234567893" in found
    assert "1234567890" not in found


def test_detect_dea_accepts_valid_rejects_bad_checksum() -> None:
    # AB1234563: (1+3+5) + 2*(2+4+6) = 33 → check digit 3. AB1234560 fails.
    found = _texts(detect_dea("DEA AB1234563 ok; AB1234560 bad."))
    assert "AB1234563" in found
    assert "AB1234560" not in found


def test_detect_vin_accepts_valid_rejects_bad_checksum() -> None:
    # 1HGCM82633A004352 is a canonical valid VIN (check digit 3 at index 8).
    found = _texts(detect_vin("VIN 1HGCM82633A004352 ok; 1HGCM82633A004353 bad."))
    assert "1HGCM82633A004352" in found
    assert "1HGCM82633A004353" not in found


def test_spans_carry_type_and_detector() -> None:
    (npi,) = list(detect_npi("NPI 1234567893 today."))
    assert npi.type == "npi"
    assert npi.detector == "phi:npi"
