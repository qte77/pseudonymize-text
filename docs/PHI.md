# PHI identifiers

*For operators redacting US healthcare identifiers.*

`pseudonymize-text` is a GDPR/PII tool; it is **not** a HIPAA Safe Harbor de-identifier
(see [COMPLIANCE.md § What we do not claim](COMPLIANCE.md#what-we-do-not-claim) and
[landscape/de-identification.md](landscape/de-identification.md)). It does detect a small set of
**checksum-validated** PHI identifiers, opt-in via `--detectors phi`.

## Detectors

| Type | Identifier | Validation |
|---|---|---|
| `npi` | National Provider Identifier (10 digits) | Luhn over the `80840` prefix (CMS check-digit spec) |
| `dea` | DEA registration number (2 letters + 7 digits) | registrant checksum (final digit) |
| `vin` | Vehicle Identification Number (17 chars) | ISO 3779 mod-11 check digit (position 9) |

Each is checksum-validated to keep false positives low, emits `<NPI:…>` / `<DEA:…>` / `<VIN:…>`
tokens, and is deterministic + reversible like every other type (canonical forms in
[HASHING.md § 2](HASHING.md#2-per-type-canonicalization)).

## Usage

Off by default. Enable the group (the `npi`/`dea`/`vin` types are already in the default `--types`):

```bash
pseudonymize detect runs/in --no-terms --detectors phi --report runs/phi.jsonl
```

Combine with the default detectors as needed: `--detectors literal,structured,phi`.

## Not covered

- **MRN** (medical record numbers) — site-specific formats with no universal checksum; supply known values via `terms.csv`.
- **Date coarsening** (HIPAA Safe Harbor §164.514(b)(2)) and **clinical NER** (a license-gated model) — tracked under [#42](https://github.com/qte77/pseudonymize-text/issues/42), not yet implemented.
- Health-plan IDs, account / certificate numbers, biometric identifiers, full-face photos, device identifiers — out of scope; use [philter](https://github.com/BCHSI/philter-ucsf) / [philter-lite](https://github.com/SironaMedical/philter-lite) or Presidio's medical recognizers.
