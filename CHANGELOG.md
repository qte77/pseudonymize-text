<!-- markdownlint-disable MD024 no-duplicate-heading -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Types of changes**: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`

<!-- scriv-insert-here -->

## [0.2.0] - 2026-05-31

Runtime sandbox + default-path cut. All runtime artefacts (key, report, mapping, term lists, plans, ignore lists) now land under `./runs/` by default; `.gitignore` ships the sandbox plus belt-and-braces per-artefact globs so default-named outputs stay out of the repo even when an operator runs outside `runs/`. Pre-1.0 behaviour change: operators relying on the previous cwd-root defaults must pass explicit `--report` / `--mapping` flags or move artefacts under `runs/`.

### Added

- `docs/assets/images/architecture-bird.svg`: hand-authored bird's-eye view of the public output lane (inputs → walker → detectors → replacer → tokenize → `./out/`) vs the secret artifacts lane (`key`, `report.jsonl`, `mapping.json`), with a trust-boundary line. Dual palette via `prefers-color-scheme`, WCAG AA-compliant green/red, responsive legend hide at <600 px. Embedded inside a collapsed `<details>` block in `docs/ARCHITECTURE.md`. Mirrors the cross-repo convention established in `qte77/doc-pipeline-engine`.
- `.gitignore`: `runs/` and `local/` sandbox directories; per-artefact globs (`*-mapping.json`, `*-report.jsonl`, `plan*.jsonl`, `discovery*.jsonl`, `ignore.txt`, `false-positives*.txt`) so default-named runtime outputs are gitignored even outside `runs/`; `terms.csv` and `terms.json` since user-provided term lists frequently contain the literal PII they are meant to mask; `!tests/fixtures/**` re-include so shipped fixtures (`tests/fixtures/terms.csv`) are not silently hidden.
- `src/pseudonymize_text/cli.py`: `_run_detect` and `_run_apply` auto-create the parent directory of `--report` (and `--mapping` in `apply`) before the first write, so the new `runs/` default works on a fresh checkout without an explicit `mkdir`.

### Fixed

- `docs/USAGE.md`: removed 9 phantom flag rows that did not exist in `cli.py:_build_parser()` (`--allow-broad-patterns`, `--ner-model`, `--ner-confidence`, `--ner-extensions`, `--ner-stoplist`, `--ner-max-bytes`, `-v` / `--verbose`, `--quiet`, `--overwrite`) — operators following the table would hit `argparse` errors.
- `docs/USAGE.md`: exit code `7` description widened to cover all three causes — `--mapping` or `--report` resolving inside `<out_dir>`, and `--plan` `config_hash` mismatch (was previously documented as `--plan`-only).
- `docs/ARCHITECTURE.md` boundary-failure-policy table + `docs/SECURITY.md` adversarial-input table: plan-file containment is enforced against `<in_dir>` (not `<out_dir>` as previously documented). Matches `cli.py:_load_plan_or_rc`.
- `docs/TERMS_CSV.md`: dead anchor `ARCHITECTURE.md#canonicalization-canonicaltext-type` repointed to `HASHING.md#2-per-type-canonicalization` (where the content actually lives).
- `docs/roadmap.md` + `README.md`: entity-type count corrected from "seven" to "eight" — default `--types` is `name,email,phone,iban,cc,ssn,org,loc`.
- `README.md` opening sentence: `addresses` → `locations` (matches the declared `loc` type).
- `docs/roadmap.md`: "Versions follow semver; `0.0.x` is the pre-implementation scaffold (current)" updated — `0.1.0` is current per CHANGELOG.
- `CHANGELOG.md`: added missing `## [0.0.2] - 2026-05-25` heading above the previously orphaned pre-implementation hardening section.

### Changed

- `NOTICE`: expanded with the standard Apache-2.0 boilerplate body and a scope note, matching `qte77/doc-pipeline-engine` NOTICE style per ADR-0006-equivalent intent (both repos chose Apache-2.0).
- `docs/GLOSSARY.md`: alphabetized abbreviations table + PII vs PHI distinction citing HIPAA Journal / GDPR Local; states tool targets GDPR personal data / PII, not PHI-only HIPAA identifier categories (#43).
- `docs/landscape/de-identification.md`: extracted from README; comparison vs Presidio + philter, "when to pick something else" matrix incl. Faker / scrubadub, rationale block for why this tool exists alongside the alternatives (#43).

### Changed

- `docs/ADR/` renamed to `docs/decisions/` for MADR canonical layout; `ADR_001` Location bullet updated; AGENTS.md and ARCHITECTURE.md link paths updated. CHANGELOG historical entries left intact per append-only principle (#43).
- `docs/COMPLIANCE.md` § "What we do not claim": new "PHI-specific identifiers" bullet narrows the disclaimer to PHI-only HIPAA categories (MRN, NPI, device IDs, etc.) and routes operators to philter / Presidio's medical recognizers (#43).
- `README.md` "Related projects" section shrunk to a one-line pointer; Documentation table extended with `docs/GLOSSARY.md` and `docs/landscape/de-identification.md` rows (#43).
- `src/pseudonymize_text/cli.py`: `--report` default `./pseudonymize-report.jsonl` → `./runs/pseudonymize-report.jsonl`; `--mapping` default `./pseudonymize-mapping.json` → `./runs/pseudonymize-mapping.json`. Behavioural change is intentional: artefacts are now sandboxed by default and the gitignore catches them whether or not an operator overrides the path.
- `README.md` Quickstart + `docs/USAGE.md` Workflow / Examples / Mail-corpus blocks: every example path migrated to `runs/in`, `runs/out`, `runs/mail-in`, `runs/mail-out`, `runs/plan.jsonl`, `runs/report.jsonl`, `runs/mapping.json`, `runs/terms.csv`, `runs/false-positives.txt`. Flag-defaults table notes parent auto-create.
- `docs/SECURITY.md` § Artifacts produced by a run: default paths updated to `./runs/pseudonymize-{report.jsonl,mapping.json}`. § Operational rules: gitignore-guidance row expanded to enumerate the runs/ sandbox plus the full per-artefact glob set.
- `docs/ARCHITECTURE.md` data-flow diagram: mapping default annotated as `runs/pseudonymize-mapping.json` with a parent-auto-create note.
- `docs/USER_STORIES.md` § Operator — re-identify: jq reverse-lookup example updated to `runs/pseudonymize-mapping.json`.
- `docs/roadmap.md`: previously planned "0.2.0 — convenience" items (`--expand-names`, pre-commit hook variant, per-language NER auto-select, `--output-format`) rolled to `0.3.0`; new `0.2.0 — runtime sandbox + default paths` section inserted; current-release line bumped to `0.2.0`.
- `docs/landscape/de-identification.md`: current-version reference bumped to `v0.2.0`.

## [0.1.0] - 2026-05-26

First implementation cut. `pseudonymize detect` / `pseudonymize apply` now wire walker → detectors → replacer → tokenize → mapping → report end-to-end against text trees and `.eml` / `.mbox` mail corpora. README quickstart is real, not aspirational.

### Added

- `src/pseudonymize_text/replacer.py`: `Span` dataclass + `apply_spans(text, spans, get_token, ignore=())` — pure span dedup (literal > structured > NER precedence, longest wins) + NFKC-casefold `--ignore` suppression + right-to-left single-pass substitution (#28).
- `src/pseudonymize_text/walker.py`: `walk_and_process(in_dir, out_dir, transform)` mirrors the input tree, routes whitelisted text through `transform`, byte-copies non-whitelisted, raises `SymlinkEscapeError` on file-symlink escapes (#29). `.mbox` extension recognised and dispatched (#40).
- `src/pseudonymize_text/formats/`: `process_eml` per ADR_002 — strips DKIM/ARC headers, pseudonymises `From`/`To`/`Cc`/`Bcc`/`Subject`/`Reply-To`, pseudonymises every `text/plain` + `text/html` part, replaces every other part with a `[part removed by pseudonymize: <ctype>; <N> bytes]` stub (#29). `process_mbox` fans out one input mbox into one `.eml` per message under `<out_dir>/<basename>/<seq>.eml`, sharing the per-message helper `transform_message` so the ADR_002 contract cannot drift between `.eml` and `.mbox` (#40).
- `src/pseudonymize_text/detectors/terms.py`: `TermRow` dataclass; `load_terms(path, *, allow_broad=False)` (CSV + JSON, broad-pattern guard rejecting `*` / `*@*` / `?` / `**`); `detect_terms(text, terms)` with `\b…\b` Unicode word boundaries, case-insensitive matching, type-aware wildcard expansion (`*@*` for email, `\d+` for IDs, etc.), `id`-grouping (#30).
- `src/pseudonymize_text/lint_terms.py` + `make lint_terms`: standalone validator that runs `load_terms`, exits non-zero on any rejected pattern; shares the helper with the runtime detector so lint and detector cannot disagree (#30).
- `src/pseudonymize_text/detectors/structured.py`: `detect_emails`, `detect_phones` (via `phonenumberslite`), `detect_ibans` (mod-97 via `python-stdnum`), `detect_credit_cards` (Luhn via `python-stdnum`), `detect_ssns` (strict US `NNN-NN-NNNN`). All canonicalisation stays in `tokenize.canonicalize` per HASHING.md §8 (#31).
- `src/pseudonymize_text/detectors/ner.py`: optional spaCy adapter (`detect_ner`) gated behind the `[ner]` extra. Lazy import; clear `ImportError` with install hint when spaCy missing. Maps PERSON / ORG / GPE / LOC → `name` / `org` / `loc` (#32).
- `docs/ner-install.md`: hash-pinned model install procedure for `xx_ent_wiki_sm==3.7.0`; `spacy download` is documented as a supply-chain hazard (#32).
- `src/pseudonymize_text/cli.py`: complete rewrite from stub. `pseudonymize detect <in_dir>` walks + detects + writes report; `pseudonymize apply <in_dir> <out_dir>` walks + detects + substitutes + writes mapping (#34). `apply --plan FILE` rehydrates spans from a prior report with config_hash + path-traversal validation (#36). `--ignore` file loader (NFKC + strip Unicode `Cf` / non-ASCII `Zs`); `--detectors LIST` / `--types LIST` filters; `--ner` flag (#38). `--report-format tsv` with per-cell formula-injection prefix on cells starting with `= + - @`; context bidi/zero-width strip; `PSEUDONYMIZE_MAX_FILE_BYTES` size cap (default 256 MB, exit 6 on overrun) (#39).
- `src/pseudonymize_text/report.py`: `TsvReportWriter` alongside the existing JSONL `ReportWriter` (#39).
- `tests/fixtures/`: shared corpus + `terms.csv` (#35).
- `tests/test_e2e.py`: detect + apply end-to-end smoke against the fixture corpus (#35).
- `Makefile`: `--cov=src/pseudonymize_text --cov-fail-under=80` on `test` (#35). `--no-cache` on the lint step so local matches CI (#33).
- `.github/workflows/python.yaml`: matching `--cov` / `--no-cache` (#35, #33).
- `README.md`: "Related projects" section with a 3-row table comparing `microsoft/presidio`, `BCHSI/philter-ucsf`, and this project (#37).
- `hypothesis>=6.0` in the dev dependency group; property test for replacer's right-to-left substitution against a naive cursor oracle (#28).

### Security

- `cli`: `--mapping` and `--report` paths inside `<out_dir>` rejected with exit 7 (#34).
- `cli`: `apply --plan` config_hash mismatch exits 7; plan-file `ReportRecord.file` containing `..` / absolute / outside-`<in_dir>` exits 4 — structure-checked before crypto check so a malicious plan with a matching key still fails path safety (#36).
- `cli`: TSV report cells whose first char is `= + - @` get a leading single quote, defeating Excel / LibreOffice formula execution on import (#39).
- `cli`: `ReportRecord.context` is stripped of U+200B–U+200F (zero-width family), U+202A–U+202E (LRE/RLE/PDF/LRO/RLO), U+2060–U+2069 (word joiner range) before being written, blocking Trojan-Source-style display reordering in any JSONL/TSV viewer (#39).
- `cli`: per-file size cap `PSEUDONYMIZE_MAX_FILE_BYTES` (default 256 MB) prevents multi-GB inputs from exhausting memory; exit 6 on overrun (#39).
- `detectors/terms`: broad-pattern guard rejects `*` / `*@*` / `?` / `**` at load time; bundled `make lint_terms` runs the same check ahead of time for CI / pre-commit (#30).
- `tests`: bidi/zero-width characters in test_cli.py spelled as `\uXXXX` escapes rather than literal source bytes, removing Trojan Source (CVE-2021-42574) exposure on the source file itself (#39).

### Changed

- `docs/ARCHITECTURE.md`: boundary-failure-policy table extended with five new rows — `walker.walk_and_process`, `detectors.terms.load_terms`, `detectors.structured.detect_*` (wrap-continue), `detectors.ner.detect_ner`, and `cli` plan loader.
- `docs/USAGE.md`: `--report PATH` flag documents containment rule (#25, pre-implementation; enforced in code in #34).

## [0.0.2] - 2026-05-25

Pre-implementation hardening pass. Strengthens the v0.0.1 primitives and prepares the docs/governance ground for the v0.1.0 implementation work. **No new runtime functionality** — `pseudonymize` CLI is still a stub. See [roadmap](docs/roadmap.md) for what 0.1.0 will add.

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
