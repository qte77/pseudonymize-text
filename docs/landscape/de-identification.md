# De-identification landscape

*For downstream pipelines and operators choosing a tool. Honest summary; pick based on the problem, not the marketing.*

This page enumerates the de-identification / pseudonymization tools we evaluated, what each is good at, and when `pseudonymize-text` is **not** the right fit.

## Comparison

| Project | License | Stance |
|---|---|---|
| [microsoft/presidio](https://github.com/microsoft/presidio) | MIT | Python-native PII detection + de-identification; covers PHI, financial PII, and generic PII. Pairs with spaCy backends. Actively maintained. One-way by default (the hash operator defaults to a random per-entity salt); reversibility via the encrypt (AES) operator requires separate key management. |
| [BCHSI/philter-ucsf](https://github.com/BCHSI/philter-ucsf) | BSD-3-Clause | Rule-based clinical-note de-identifier; HIPAA Safe Harbor coverage. Redacts text; not reversible. **Stale** — last release 2020. |
| [SironaMedical/philter-lite](https://github.com/SironaMedical/philter-lite) | BSD-3-Clause | Maintained, pip-installable refactor of philter-ucsf (releases through 2026). Same one-way clinical-PHI redaction; not reversible. |
| [joke2k/faker](https://github.com/joke2k/faker) | MIT | Synthetic-data **generator**, not a de-identifier — fabricates new values unrelated to the input. Actively maintained; listed only as a contrast. |
| [LeapBeyond/scrubadub](https://github.com/LeapBeyond/scrubadub) | MIT | Library-API PII redaction; swaps entities for typed placeholders (`{{EMAIL}}`). Not reversible. **Stale** — last release 2023. |

## When `pseudonymize-text` is the right fit

- You need **deterministic, reversible** pseudonymization (HMAC-SHA256 + secret key + mapping file) so the same plaintext produces the same token across runs and machines.
- You want an **audit-first** workflow — `detect` writes a JSONL plan, `apply` executes it byte-identically.
- Your corpus is GDPR / EDPB / ENISA / NIST-governed and you need a mapping of design choices to those standards (see [COMPLIANCE.md](../COMPLIANCE.md)).
- You're processing **text files in folder trees** (`.txt`, `.md`, `.log`, `.py`, `.json`, `.yaml`, `.csv`, `.ini`, `.eml`, `.mbox`) and want a CLI that mirrors `in/` → `out/`.

## When to pick something else

| If you need | Use |
|---|---|
| HIPAA Safe Harbor coverage of clinical notes | [philter-ucsf](https://github.com/BCHSI/philter-ucsf), or its maintained fork [philter-lite](https://github.com/SironaMedical/philter-lite) |
| Broad multi-language PII detection out of the box with mature ML recognizers | [Presidio](https://github.com/microsoft/presidio) |
| Synthetic data generation rather than reversible pseudonymization | [Faker](https://github.com/joke2k/faker) |
| Library-API PII redaction with typed placeholders (Python) | [scrubadub](https://github.com/LeapBeyond/scrubadub) (last release 2023) |
| PHI-specific identifiers (MRN, NPI, DEA, VIN, device IDs) | [philter](https://github.com/BCHSI/philter-ucsf) or Presidio's medical recognizers — **not** detected by `pseudonymize-text` (see [GLOSSARY.md § PII vs PHI](../GLOSSARY.md#pii-vs-phi)) |

## Mail corpora

| Mail corpus shape | Pick | Why |
|---|---|---|
| Corporate / GDPR-governed | `pseudonymize-text` | Format fidelity per [ADR_002](../decisions/ADR_002.md); deterministic + reversible-under-control per [COMPLIANCE.md § Requirements satisfied](../COMPLIANCE.md#requirements-satisfied); audit-first detect/apply |
| Clinical (patient correspondence, EHR exports) | [philter](https://github.com/BCHSI/philter-ucsf) on extracted body text, or track [#42](https://github.com/qte77/pseudonymize-text/issues/42) | PHI-only HIPAA identifiers (MRN, NPI, device IDs) are out of scope for `pseudonymize-text`; you trade mail-structure fidelity for Safe Harbor coverage |
| Mixed (mostly PII + a few PHI patterns) where reversibility matters¹ | `pseudonymize-text` + hand-curated `terms.csv` listing known PHI strings | One pipeline; gaps stay explicit in `terms.csv` |
| Mail files >256 MB | Pre-split `.mbox` via Python stdlib [`mailbox`](https://docs.python.org/3/library/mailbox.html), then `pseudonymize-text` | Streaming deferred to 2.0.0 per [roadmap.md](../roadmap.md) |

¹ Operator-derivable from literal-precedence rules ([ARCHITECTURE.md § Span precedence](../ARCHITECTURE.md#span-precedence-overlap-resolution-in-replacerpy)); not separately documented as a supported workflow.

## Why this tool exists alongside the above

Presidio and philter are mature; neither targets the specific intersection of:

1. **Deterministic + reversible by design** (Presidio's hash operator uses a random salt; reversibility needs the separate encrypt operator with AES key management. philter is one-way.).
2. **GDPR Art. 4(5) framing** with EDPB 01/2025 / ENISA Advanced / NIST SP 800-188 references baked into the documentation rather than added post-hoc.
3. **Audit-first two-step CLI** — operators review a JSONL plan before any byte of output is written.
4. **Stdlib-first dependency surface** — `python-stdnum` + `phonenumberslite` + Pydantic; spaCy gated behind a `[ner]` extra.

If those four items are not load-bearing for your use case, Presidio or philter is likely the faster path.

## Status

`pseudonymize-text` is at v0.2.0 ("detect / apply pipeline shipped"). The [public Python API](../roadmap.md) (`pseudonymize_text.transform(...)`) is not stabilized until 1.0.0; current downstream consumers should pin to a specific git tag and use the CLI rather than importing internal modules.
