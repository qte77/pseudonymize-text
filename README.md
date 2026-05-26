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
| [docs/landscape/de-identification.md](docs/landscape/de-identification.md) | Alternatives (Presidio, philter) and when to pick them |
| [docs/ADR/](docs/ADR/) | Architectural decisions ([MADR](https://adr.github.io/madr/) format) |
| [AGENTS.md](AGENTS.md) | Behavioral rules for AI coding agents |
| [CHANGELOG.md](CHANGELOG.md) | Version history (Keep-a-Changelog) |

## Related projects

If `pseudonymize-text` is the wrong fit, see [docs/landscape/de-identification.md](docs/landscape/de-identification.md) for an honest comparison against [Presidio](https://github.com/microsoft/presidio) (broader detection, separate key management for reversibility) and [philter](https://github.com/BCHSI/philter-ucsf) (HIPAA Safe Harbor for clinical notes; not reversible).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
