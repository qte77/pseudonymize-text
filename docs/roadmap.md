# Roadmap

For anyone planning work or comparing milestones. Concrete actionable tasks live in [GitHub Issues](https://github.com/qte77/pseudonymize-text/issues), not here.

Versions follow semver; current release is `0.2.0` (see [CHANGELOG.md](../CHANGELOG.md)). `0.0.x` was the pre-implementation scaffold.

## Scope philosophy

**Modular, not broad.** Core stays narrow — text trees, mail (`.eml` / `.mbox`), and eight entity types via literal / structured / NER detectors. New capabilities ship as opt-in groups/extras (`[ner]` extra today; the `phi` detector group — checksum NPI/DEA/VIN — shipped via `--detectors phi` per [#42](https://github.com/qte77/pseudonymize-text/issues/42), with clinical NER / MRN / date-coarsening deferred; `[office]` deferred to 2.0). This preserves the stdlib-first dependency surface and the audit-first positioning. Pick Presidio for broader ML detection or philter for HIPAA Safe Harbor — see [landscape/de-identification.md](landscape/de-identification.md).

**Not on the roadmap.** Real-time HTTP / middleware redaction, image OCR / scanned-document PII, database column redaction at query time, and a GUI / web UI are explicitly **not** scoped — different products solve those.

## 0.1.0 — implementation

Goal: ship the contract documented in [README](../README.md) and [docs/](.).

Build order chosen for testability — primitives first (no I/O, no third-party deps), then detectors (each independently testable), then orchestration:

1. Package scaffold — pyproject, Makefile, `src/pseudonymize_text/`, `tests/`, CI (**done** in 0.0.1).
2. `tokenize.py` + `mapping.py` + `report.py` — pure functions over strings and dicts; no filesystem in `tokenize.py`. Pydantic v2 models at I/O boundaries (`MappingRecord`, `ReportHeader`, `ReportRecord`); `Span` stays stdlib `dataclass`.
3. `replacer.py` — span dedup + right-to-left substitution. Pure over `(text, spans)`.
4. `walker.py` — folder mirror, extension whitelist, atomic writes.
5. `detectors/terms.py` — literal + pattern + `id`-grouping; CSV/JSON loader.
6. `detectors/structured.py` — email, phone (`phonenumberslite`), IBAN/CC (`python-stdnum`), SSN.
7. `detectors/ner.py` — spaCy adapter behind `[ner]` extra; default off.
8. `cli.py` — `detect` and `apply` subcommands wiring the above.
9. End-to-end tests + sample term lists in `tests/fixtures/`.

## 0.2.0 — runtime sandbox + default paths

Goal: keep runtime artefacts out of the repo by default and align CLI defaults with the documented `runs/` convention.

- `.gitignore` ships a `runs/` (+ `local/`) sandbox plus per-artefact globs (`*-mapping.json`, `*-report.jsonl`, `plan*.jsonl`, `discovery*.jsonl`, `false-positives*.txt`, `ignore.txt`) and term-list globs (`terms.csv`, `terms.json`); `!tests/fixtures/**` re-include protects shipped fixtures.
- `cli.py`: `--report` and `--mapping` default to `./runs/pseudonymize-{report.jsonl,mapping.json}`; parent directory is auto-created on first write.
- Docs (`README.md`, `docs/USAGE.md`, `docs/SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/USER_STORIES.md`) re-aligned with the convention.

## 0.3.0 — convenience

- `--expand-names` auto-variants (with collision detection).
- Pre-commit hook variant.
- Per-language NER model auto-selection.
- `--output-format` flag — emit tokens as `[[TYPE:hex]]` (or another non-angle-bracket delimiter) for LLM-bound corpora that need to avoid chat-template special-token collisions. See [HASHING.md §9](HASHING.md#9-output-format).

## 1.0.0 — public API + reverse

- Public Python API: `pseudonymize_text.transform(text, config) -> (text, mapping_delta, report_records)`. Locks the surface that downstream pipelines (e.g. `doc-pipeline-engine`) call.
- `pseudonymize reverse <token>` subcommand.
- Manual key-rotation tool.
- Truncation-length flag (raise above 128 bits for corpora > 10¹⁵ tokens).

## 2.0.0 — formats and scale

- PDF and Office (`.docx`, `.xlsx`) input.
- Streaming for files larger than memory.
- Parallel file processing.
- SQLite mapping backend (alternative to JSON for very large mappings).
- Encrypted mapping at rest.
- SARIF report format.
- GLiNER and HuggingFace NER backends.

## See also

- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — module layout and stage graph.
- [docs/HASHING.md](HASHING.md) — token construction and stability rules (frozen contract; v0.1 must implement exactly this).
