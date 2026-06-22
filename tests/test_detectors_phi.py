"""PHI detector tests (issue #42): NPI / DEA / VIN checksum validation."""

from collections.abc import Iterable

from pseudonymize_text.detectors.phi import (
    detect_dea,
    detect_mrn,
    detect_npi,
    detect_vin,
)
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


# --- Contextual MRN (E2-A) ---------------------------------------------------
# MRNs have no checksum, so detection is gated on a nearby cue word and is
# higher false-positive than the checksum-validated types above.


def test_detect_mrn_with_preceding_cue() -> None:
    (mrn,) = list(detect_mrn("Patient MRN 1234567 admitted"))
    assert (mrn.type, mrn.text, mrn.detector) == ("mrn", "1234567", "phi:mrn")


def test_detect_mrn_with_following_cue() -> None:
    assert _texts(detect_mrn("1234567 (Medical Record Number)")) == {"1234567"}


def test_detect_mrn_cue_case_insensitive() -> None:
    assert _texts(detect_mrn("mrn: 7654321")) == {"7654321"}


def test_detect_mrn_requires_a_cue() -> None:
    assert list(detect_mrn("Order number 1234567 shipped")) == []


def test_detect_mrn_ignores_too_short_runs() -> None:
    assert list(detect_mrn("MRN 12345")) == []


def test_detect_mrn_context_window_boundary() -> None:
    near = "MRN" + " " * 60 + "123456"
    far = "MRN" + " " * 61 + "123456"
    assert _texts(detect_mrn(near)) == {"123456"}
    assert list(detect_mrn(far)) == []
