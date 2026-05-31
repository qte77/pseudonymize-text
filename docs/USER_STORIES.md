# User Stories

*For prospective adopters and downstream pipeline authors deciding whether `pseudonymize-text` fits.*

User stories use the form "As a `<role>`, I want `<capability>`, so that `<outcome>`." A story is **supported** if existing features cover it, **partial** if it needs a hand-curated `terms.csv` or out-of-band tooling, **out of scope** if it requires an architectural change.

## Supported

### Operator — bulk redact a folder tree before distribution

As a data engineer with a tree of `.txt` / `.csv` / `.eml` files containing PII, I want to substitute every name / email / phone / IBAN / credit card / SSN / organization with a stable token, so that I can hand the tree to a downstream consumer without leaking individual identity but retain joinability across files.

→ Covered by `pseudonymize apply <in> <out> --terms terms.csv`. See [USAGE.md](USAGE.md).

### DPO / auditor — verify what was substituted before any output is written

As a Data Protection Officer reviewing a pseudonymization run, I want to see a complete JSONL plan of every span the tool intends to substitute before any byte of output is written, so that I can sign off on the operation as compliant under GDPR Art. 4(5).

→ Covered by `pseudonymize detect → review plan.jsonl → apply --plan plan.jsonl`. See [USAGE.md § Workflow](USAGE.md#workflow) and [COMPLIANCE.md](COMPLIANCE.md).

### Operator — re-identify a single record under controlled access

As an operator responding to an authorized data-subject access request, I want to look up the plaintext value behind a `<TYPE:hex>` token from a sealed mapping file, so that I can produce the original record without rolling back the entire dataset.

→ Covered today by `jq -r '.["<NAME:7f3a…>"].value' runs/pseudonymize-mapping.json`; a `pseudonymize reverse` subcommand is planned for 1.0.0. See [SECURITY.md § Reverse lookup](SECURITY.md#reverse-lookup).

### Pipeline author — pseudonymize a mail corpus while preserving MIME structure

As a pipeline author processing a mailbox, I want headers, `text/plain`, and `text/html` parts pseudonymized while non-text attachments are stubbed and DKIM / ARC headers stripped, so that the output is still a valid `.eml` consumable by downstream mail clients without leaking PII.

→ Covered by automatic routing of `.eml` / `.mbox` through `formats/` per [ADR_002](decisions/ADR_002.md). See [USAGE.md Examples](USAGE.md#examples) and [landscape/de-identification.md § Mail corpora](landscape/de-identification.md#mail-corpora).

### Compliance officer — defend the design against GDPR Art. 4(5) requirements

As a compliance officer documenting our pseudonymization controls, I want a per-requirement mapping of design choices to GDPR / EDPB / ENISA / NIST sources, so that I can pass an audit without re-deriving the rationale.

→ Covered by [COMPLIANCE.md § Requirements satisfied](COMPLIANCE.md#requirements-satisfied).

## Partial

### Operator — patch coverage of clinical PHI patterns

As an operator with mostly-PII corpora that sprinkle in PHI-shaped identifiers (MRN-like or NPI-like), I want literal `terms.csv` entries to take precedence over structured / NER detectors so I can patch coverage without forking the tool.

→ Partial: `terms.csv` literal entries beat structured / NER per [ARCHITECTURE.md § Span precedence](ARCHITECTURE.md#span-precedence-overlap-resolution-in-replacerpy). Gaps stay explicit; no automatic PHI detection. Track [#42](https://github.com/qte77/pseudonymize-text/issues/42) for a `[phi]` extra.

### Pipeline author — embed in a Python application

As a Python application author, I want to call `pseudonymize_text.transform(text, config)` from in-process code without spawning the CLI.

→ Partial: detector / replacer / tokenizer modules are importable but the **public** API is not stabilized until 1.0.0 per [roadmap.md](roadmap.md). Pin to a specific git tag and accept breakage on internal-module changes.

## Out of scope

### Clinical-grade HIPAA Safe Harbor de-identification

**Why**: PHI-only HIPAA identifier categories (MRN, NPI, account numbers, certificate / license numbers, device identifiers, biometric identifiers, full-face photos) are not detected. Use [philter](https://github.com/BCHSI/philter-ucsf) or Presidio's medical recognizers.

### Anonymization (vs pseudonymization)

**Why**: Tokens are reversible by design (mapping + key). To get one-way de-identification, either use philter, or discard the mapping **and** key after `apply` per [SECURITY.md § Permanent de-identification](SECURITY.md#permanent-de-identification).

### Image / scanned-document PII redaction

**Why**: Different input modality (OCR pipeline). Presidio Image Redactor / NLM Scrubber / pydicom `deid` cover this; see [landscape/de-identification.md](landscape/de-identification.md).

### Real-time HTTP / streaming PII middleware

**Why**: Batch tool, not in-process runtime. Use [scrubadub](https://github.com/LeapBeyond/scrubadub) for runtime Python redaction.

### Multi-tenant key separation within one process

**Why**: One HMAC key per run. Operators needing per-tenant keys run the tool once per tenant with a distinct `--key-file`.

### GUI / web UI

**Why**: CLI-only by design (auditability + scriptability). Not on the roadmap.

## See also

- [README.md § Use cases](../README.md#use-cases) — quick covered / not-covered / deferred summary.
- [docs/landscape/de-identification.md](landscape/de-identification.md) — tool-selection guide vs Presidio / philter / Faker / scrubadub.
- [docs/roadmap.md § Scope philosophy](roadmap.md#scope-philosophy) — modular-vs-broad steering principle.
- [docs/ARCHITECTURE.md § Out of architectural scope](ARCHITECTURE.md#out-of-architectural-scope) — design-level non-support.
