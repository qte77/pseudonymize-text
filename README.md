# pseudonymize

Bulk-pseudonymize sensitive entities (names, emails, phones, IBANs, SSNs, credit cards, addresses, organizations) across a folder tree — deterministically and reversibly.

[![License](https://img.shields.io/badge/license-Apache--2.0-58f4c2.svg)](LICENSE)
![Version](https://img.shields.io/badge/version-0.1.0-58f4c2.svg)
[![CodeFactor](https://www.codefactor.io/repository/github/qte77/pseudonymize-text/badge)](https://www.codefactor.io/repository/github/qte77/pseudonymize-text)
[![python](https://github.com/qte77/pseudonymize-text/actions/workflows/python.yaml/badge.svg)](https://github.com/qte77/pseudonymize-text/actions/workflows/python.yaml)
[![markdownlint](https://github.com/qte77/pseudonymize-text/actions/workflows/markdownlint.yaml/badge.svg)](https://github.com/qte77/pseudonymize-text/actions/workflows/markdownlint.yaml)
[![links](https://github.com/qte77/pseudonymize-text/actions/workflows/links.yaml/badge.svg)](https://github.com/qte77/pseudonymize-text/actions/workflows/links.yaml)

- **Deterministic** — same input + same key → same token, every run, every machine.
- **Reversible** via the mapping file (kept separate from output and key).
- **GDPR/ENISA-aligned** — HMAC-SHA256 with secret key, namespaced per entity type; mapping and key never co-located with output. See [docs/COMPLIANCE.md](docs/COMPLIANCE.md).
- **Lightweight** — Python stdlib + two small deps (`python-stdnum`, `phonenumberslite`). Optional spaCy NER via `[ner]` extra.
- **Audit-first** — `detect` produces a JSONL plan; `apply` executes it byte-identically.

## Use cases

**Covered**: bulk pseudonymization of text trees (`.txt`, `.md`, `.log`, `.py`, `.json`, `.yaml`, `.csv`, `.toml`, `.ini`) and mail corpora (`.eml`, `.mbox`); seven entity types (name, email, phone, IBAN, credit card, SSN, organization, location) via literal + structured detectors plus optional spaCy NER; deterministic + reversible HMAC-SHA256 with an audit-first detect/apply CLI.

**Not covered**: PHI-only HIPAA identifiers (MRN, NPI, device IDs, biometric); anonymization (output is still personal data); linkage attacks via writing style / timestamps / metadata; binary mail attachments (dropped with stub); image OCR; database column redaction at query time; real-time HTTP middleware redaction. See [docs/USER_STORIES.md](docs/USER_STORIES.md) for capability-level coverage and [docs/COMPLIANCE.md § What we do not claim](docs/COMPLIANCE.md#what-we-do-not-claim) for the formal non-claims.

**Deferred**: PDF and Office formats, streaming for files > 256 MB, parallel processing, encrypted mapping at rest, public Python API — see [docs/roadmap.md](docs/roadmap.md).

## Install

```bash
uv add pseudonymize           # core
uv add 'pseudonymize[ner]'    # optional spaCy NER
```

## Quickstart

```bash
# 1. Generate a secret key (one-time, store outside the repo)
openssl rand -hex 32 > .key

# 2. Detect — writes a JSONL report; no changes to inputs or outputs
PSEUDONYMIZE_KEY=$(cat .key) \
  pseudonymize detect ./input --terms terms.csv --report report.jsonl

# 3. Review report.jsonl, then apply
PSEUDONYMIZE_KEY=$(cat .key) \
  pseudonymize apply ./input ./output --terms terms.csv --plan report.jsonl
```

`./output` mirrors `./input` with sensitive strings replaced by `<TYPE:hash>` tokens (e.g. `<NAME:7f3a9c8b…>`). `pseudonymize-mapping.json` is written next to (not inside) `./output`.

## Documentation

| Doc | Purpose |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Modules, data flow, stack |
| [docs/USAGE.md](docs/USAGE.md) | CLI reference: subcommands, flags, exit codes |
| [docs/TERMS_CSV.md](docs/TERMS_CSV.md) | Input schema (`id`, `value`, `type`, wildcards) |
| [docs/COMPLIANCE.md](docs/COMPLIANCE.md) | GDPR / ENISA / EDPB / NIST posture |
| [docs/SECURITY.md](docs/SECURITY.md) | Threat model, key & mapping handling |
| [docs/HASHING.md](docs/HASHING.md) | Token construction, canonicalization, stability — design rationale |
| [docs/GLOSSARY.md](docs/GLOSSARY.md) | Abbreviations, PII vs PHI, terms of art |
| [docs/USER_STORIES.md](docs/USER_STORIES.md) | User stories grouped by support level (supported / partial / out of scope) |
| [docs/landscape/de-identification.md](docs/landscape/de-identification.md) | Alternatives (Presidio, philter) and when to pick them |
| [docs/decisions/](docs/decisions/) | Architectural decisions ([MADR](https://adr.github.io/madr/) format) |
| [AGENTS.md](AGENTS.md) | Behavioral rules for AI coding agents |
| [CHANGELOG.md](CHANGELOG.md) | Version history (Keep-a-Changelog) |

## Related projects

If `pseudonymize-text` is the wrong fit, see [docs/landscape/de-identification.md](docs/landscape/de-identification.md) for an honest comparison against [Presidio](https://github.com/microsoft/presidio) (broader detection, separate key management for reversibility) and [philter](https://github.com/BCHSI/philter-ucsf) (HIPAA Safe Harbor for clinical notes; not reversible).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
