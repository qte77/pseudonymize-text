# Roadmap

For anyone planning work or comparing milestones. Concrete actionable tasks live in [GitHub Issues](https://github.com/qte77/pseudonymize-text/issues), not here.

Versions follow semver; `0.0.x` is the pre-implementation scaffold (current).

## 0.1.0 — implementation

Goal: ship the contract documented in [README](../README.md) and [docs/](.).

Build order chosen for testability — primitives first (no I/O, no third-party deps), then detectors (each independently testable), then orchestration:

1. Package scaffold — pyproject, Makefile, `src/pseudonymize_text/`, `tests/`, CI (**done** in 0.0.1).
2. `tokenize.py` + `mapping.py` + `report.py` — pure functions over strings and dicts; no filesystem; no third-party.
3. `replacer.py` — span dedup + right-to-left substitution. Pure over `(text, spans)`.
4. `walker.py` — folder mirror, extension whitelist, atomic writes.
5. `detectors/terms.py` — literal + pattern + `id`-grouping; CSV/JSON loader.
6. `detectors/structured.py` — email, phone (`phonenumberslite`), IBAN/CC (`python-stdnum`), SSN.
7. `detectors/ner.py` — spaCy adapter behind `[ner]` extra; default off.
8. `cli.py` — `detect` and `apply` subcommands wiring the above.
9. End-to-end tests + sample term lists in `tests/fixtures/`.

## 0.2.0 — convenience

- `--expand-names` auto-variants (with collision detection).
- Pre-commit hook variant.
- Per-language NER model auto-selection.

## 1.0.0 — public API + reverse

- Public Python API: `pseudonymize_text.transform(text, config) -> (text, mapping_delta, report_records)`. Locks the surface that downstream pipelines (e.g. `doc-pipeline-engine`) call.
- `pseudonymize reverse <token>` subcommand.
- Pydantic v2 contract models for `Span`, `MappingEntry`, `ReportRecord`.
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
