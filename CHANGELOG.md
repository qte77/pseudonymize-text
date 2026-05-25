<!-- markdownlint-disable MD024 no-duplicate-heading -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Types of changes**: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`

## [Unreleased]

### Added

- `docs/ADR/`: MADR-format architectural decision records, filename pattern `ADR_###.md` (#20)
- `docs/ADR/ADR_001.md`: adopt MADR for ADRs (#20)
- `docs/ADR/ADR_002.md`: mail-part handling for `.eml` / `.mbox` — pseudonymize `text/plain` + `text/html` parts and listed headers, drop non-text parts with a stub, strip `DKIM-Signature` / `ARC-*`, fan out `.mbox` to one `.eml` per message (#20)
- `docs/ARCHITECTURE.md`: `formats/` entry in module layout; "Mail-format support" section linking ADR_002 (#20); walker-behavior row for file-symlink containment under `<in_dir>` (#25); boundary-failure-policy row for `cli` plan-file containment (#25)
- `docs/SECURITY.md`: operational-rules row enforcing `--report` outside `<out_dir>` (exit 7); "In-scope adversarial inputs" table (ReDoS / Unicode / plan-path / size guards); "LLM and downstream consumption" section — prompt-injection passthrough non-claim, mapping/report-not-for-LLM-chats rule, `<TYPE:hex>` chat-template collision caveat (#25)
- `docs/HASHING.md` §9: caveat that `<TYPE:hex>` may collide with chat-template special tokens; link to planned `--output-format` (#25)
- `docs/USAGE.md`: `--report PATH` documents containment rule (#25)
- `docs/roadmap.md`: 0.2.0 — `--output-format` for LLM-bound corpora (#25)
- `AGENTS.md`: ADR directory in authoritative sources (#20); non-negotiable rule forbidding agent reads of `.key` / mapping / report files and writes of secrets under `~/.claude/` (#21)
- `README.md`: ADR directory in doc index (#20)
- `.github/CODEOWNERS`: human-review gate on `tokenize.py`, `mapping.py`, `_schemas.py` (#21)
- `.gitignore`: `.key`, `*.key`, `pseudonymize-mapping.json`, `pseudonymize-report.jsonl` (#21); Python build / cache artefacts (`__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.ruff_cache/`)

### Changed

- `src/pseudonymize_text/mapping.py`: `save_mapping` now opens the tmp file via `os.open` with mode `0o600` instead of `Path.write_text`, decoupling from process umask (#22)
- `src/pseudonymize_text/tokenize.py`: `hmac_token` drops the raw `key` parameter immediately after deriving `mac_key` and `del`s `mac_key` in a `finally` block so neither survives in `f_locals` if the HMAC computation raises (#24)
- `docs/ARCHITECTURE.md`: boundary-failure-policy notes for `mapping.save_mapping` (0o600 tmp file) and `tokenize.hmac_token` (frame-locals scrub) record the security intent inline (#22, #24)

### Fixed

- `src/pseudonymize_text/_schemas.py`: `ReportHeader.config_hash` constrained to `Field(pattern=r"^[0-9a-f]{32}$")`; non-hex strings now fail Pydantic validation at the I/O boundary (#23)

### Security

- Mapping tmp file is no longer world-readable on `umask 022` hosts during the write window between create and atomic rename (#22)
- HMAC key and derived `mac_key` cannot leak through traceback frames into crash reporters, `--verbose` dumps, or callers that snapshot `__traceback__.tb_frame.f_locals` (#24)
- Report header `config_hash` field cannot accidentally hold raw key material or any non-truncated hash; rejected at schema load (#23)

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
