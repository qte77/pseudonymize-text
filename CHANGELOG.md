<!-- markdownlint-disable MD024 no-duplicate-heading -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Types of changes**: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`

## [Unreleased]

## [0.0.1] - 2026-05-22

### Added

- `src/pseudonymize_text/tokenize.py`: `hmac_token()` per HASHING.md §1 (HMAC-SHA256, 128-bit truncation, `<TYPE:hex>` wrapping) and `canonicalize()` per HASHING.md §2 (per-type rules for name/org/loc/email/phone/iban/cc/ssn)
- `src/pseudonymize_text/mapping.py`: `load_mapping()`, `save_mapping()` (atomic tmp + `os.replace`), `upsert()` (preserves `first_seen`, sums `occurrences`)
- `src/pseudonymize_text/report.py`: `ReportWriter` with header-once invariant (header on first `write()`, records thereafter)
- `src/pseudonymize_text/_schemas.py`: pydantic models `MappingRecord`, `ReportHeader`, `ReportRecord` with field constraints (line/col ≥ 1, start/end ≥ 0, detector + token regex)
- `src/pseudonymize_text/cli.py`, `__init__.py`: package skeleton, stub CLI, exposed `__version__`
- `docs/`: ARCHITECTURE.md, USAGE.md, HASHING.md, COMPLIANCE.md, SECURITY.md, TERMS_CSV.md, roadmap.md — design rationale, CLI contract, hashing spec, compliance/security posture, terms-list schema, milestones
- `docs/ARCHITECTURE.md`: **Working norms** section — boundary failure-policy table (`fail-loud` / `wrap-degrade` / `wrap-continue`) and TDD per-behaviour discipline (Red → Green per observable behaviour)
- `.github/workflows/`: `python.yaml` (ruff + pytest on 3.11/3.12/3.13), `markdownlint.yaml`, `links.yaml` (lychee, weekly schedule)
- `Makefile`, `pyproject.toml`, `uv.lock`: hatchling build, Python ≥3.11, `python-stdnum` + `phonenumberslite` core deps, optional `[ner]` extra for spaCy, dev group with pytest + ruff, `pseudonymize` CLI entry point
- `tests/`: round-trip + atomicity tests for mapping, HMAC byte-for-byte vectors and canonicalization rules for tokenize, header-once invariant for report, smoke tests for package + CLI
- `LICENSE`, `NOTICE`: Apache-2.0 with patent grant and NOTICE-file mechanism
- `.markdownlint.json`, `.gitignore`: lint config and tracked-artifact ignores

### Changed

- `pyproject.toml`: `ruff.lint.select` extended to full hardening set (`E F I N W UP B S SIM RUF PT ANN TC PGH C90 D TRY`); `mccabe.max-complexity = 10`; per-file ignores for tests (S101, D, S105, S106) and scripts (D, ANN)
- `docs/HASHING.md`: factual corrections — §3 reframed (ambiguity prevention, not attack prevention); §6 collision math fixed (n²/2¹²⁹, not 64-bit); §8 split into locked vs not-locked dependencies; §10 added `last_seen` and load/merge/atomic-write semantics; §11 trust-boundary reasoning

### Security

- HMAC-SHA256 with secret key required at runtime; key never logged or persisted in mapping file
- Atomic mapping writes via tmp-file + `os.replace` prevent partial-corruption on crash
