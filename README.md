# pseudonymize-text

> Bulk-pseudonymize sensitive entities (names, emails, phones, IBANs, SSNs, credit cards, locations, organizations) across a folder tree — deterministically and reversibly.

[![License](https://img.shields.io/badge/license-Apache--2.0-58f4c2.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-58f4c2.svg)](CHANGELOG.md)
[![CodeQL](https://github.com/qte77/pseudonymize-text/actions/workflows/codeql.yaml/badge.svg)](https://github.com/qte77/pseudonymize-text/actions/workflows/codeql.yaml)
[![CodeFactor](https://www.codefactor.io/repository/github/qte77/pseudonymize-text/badge)](https://www.codefactor.io/repository/github/qte77/pseudonymize-text)
[![python](https://github.com/qte77/pseudonymize-text/actions/workflows/python.yaml/badge.svg)](https://github.com/qte77/pseudonymize-text/actions/workflows/python.yaml)
[![markdownlint](https://github.com/qte77/pseudonymize-text/actions/workflows/markdownlint.yaml/badge.svg)](https://github.com/qte77/pseudonymize-text/actions/workflows/markdownlint.yaml)
[![links](https://github.com/qte77/pseudonymize-text/actions/workflows/links.yaml/badge.svg)](https://github.com/qte77/pseudonymize-text/actions/workflows/links.yaml)

## What

- **Deterministic** — same input + same key → same token, every run, every machine.
- **Reversible** via the mapping file (kept separate from output and key).
- **GDPR/ENISA-aligned** — HMAC-SHA256 with secret key, namespaced per entity type; mapping and key never co-located with output. See [docs/COMPLIANCE.md](docs/COMPLIANCE.md).
- **Lightweight** — Python stdlib + two small deps (`python-stdnum`, `phonenumberslite`). Optional spaCy NER via `[ner]` extra.
- **Audit-first** — `detect` produces a JSONL plan; `apply` executes it byte-identically.

> **What this isn't** — not anonymization (output is still personal data). Detectors are jurisdiction-tagged ([ADR_003 coverage table](docs/decisions/ADR_003.md#detector-coverage-by-jurisdiction-source-of-truth)): international + US default, with opt-in US PHI (NPI/DEA/VIN, plus context-cued MRN via `--phi-context`; see [docs/PHI.md](docs/PHI.md)) and EU national IDs (`--detectors eu`). Device IDs, image OCR, and binary mail attachments stay out of scope. See [docs/USER_STORIES.md](docs/USER_STORIES.md) for coverage by support level and [docs/COMPLIANCE.md § What we do not claim](docs/COMPLIANCE.md#what-we-do-not-claim) for the formal non-claims.

## How

```bash
# install (core; the spaCy NER extra is optional)
uv add pseudonymize-text          # or: uv add 'pseudonymize-text[ner]'

# 1. Generate a secret key (one-time, store outside the repo)
openssl rand -hex 32 > .key

# 2. Detect — writes a JSONL report; no changes to inputs or outputs
PSEUDONYMIZE_KEY=$(cat .key) \
  pseudonymize detect runs/in --terms runs/terms.csv --report runs/plan.jsonl

# 3. Review the plan, then apply
PSEUDONYMIZE_KEY=$(cat .key) \
  pseudonymize apply runs/in runs/out --terms runs/terms.csv --plan runs/plan.jsonl
```

`runs/out` mirrors `runs/in` with sensitive strings replaced by `<TYPE:hash>` tokens (e.g. `<NAME:7f3a9c8b…>`); `runs/pseudonymize-mapping.json` is written next to (not inside) `runs/out`, and the whole `runs/` tree is gitignored. See [docs/USAGE.md](docs/USAGE.md) for the full CLI reference.

## Why

Reversible pseudonymization sits between one-way redaction and full anonymization. Incumbents differ on that axis: [Presidio](https://github.com/microsoft/presidio) needs separate key management for reversibility, and [philter](https://github.com/BCHSI/philter-ucsf) is one-way by design. `pseudonymize-text` makes deterministic, key-reversible HMAC-SHA256 tokens the default — with an audit-first detect/apply CLI and a stdlib-first dependency surface. See [docs/landscape/de-identification.md](docs/landscape/de-identification.md) for an honest comparison and when to pick something else.

## Refs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — modules, data flow, stack
- [docs/USAGE.md](docs/USAGE.md) — CLI reference: subcommands, flags, exit codes
- [docs/TERMS_CSV.md](docs/TERMS_CSV.md) — term-list input schema
- [docs/COMPLIANCE.md](docs/COMPLIANCE.md) — GDPR / ENISA / EDPB / NIST posture
- [docs/SECURITY.md](docs/SECURITY.md) — threat model, key & mapping handling
- [docs/HASHING.md](docs/HASHING.md) — token construction, canonicalization, stability
- [docs/GLOSSARY.md](docs/GLOSSARY.md) — abbreviations, PII vs PHI
- [docs/USER_STORIES.md](docs/USER_STORIES.md) — user stories by support level
- [docs/roadmap.md](docs/roadmap.md) — roadmap and deferred features
- [docs/landscape/de-identification.md](docs/landscape/de-identification.md) — alternatives and when to pick them
- [docs/decisions/](docs/decisions/) — architectural decisions ([MADR](https://adr.github.io/madr/) format)
- [CONTRIBUTING.md](CONTRIBUTING.md) — contributor workflow, commands, releasing
- [CHANGELOG.md](CHANGELOG.md) — version history (Keep a Changelog)

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
