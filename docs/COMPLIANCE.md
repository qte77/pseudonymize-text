# Compliance Posture

*For auditors and DPOs evaluating the tool's GDPR/ENISA posture.*

This document maps design decisions to the regulatory requirements they satisfy. It also enumerates what the tool does **not** claim.

## Scope

- **Pseudonymization**, in the GDPR Art. 4(5) sense — replacement of identifiers with tokens such that the data can no longer be attributed to a specific person without additional information held separately.
- Not anonymization. Tokenized output remains personal data and full GDPR obligations apply.
- Not differential privacy, k-anonymity, or generalization.

## Regulatory references

| Source | Relevance |
|---|---|
| GDPR Art. 4(5) | Definition of pseudonymization. <https://eur-lex.europa.eu/eli/reg/2016/679/oj> |
| EDPB Guidelines 01/2025 on pseudonymisation | Current EU supervisory guidance. <https://www.edpb.europa.eu/system/files/2025-01/edpb_guidelines_202501_pseudonymisation_en.pdf> |
| ENISA — *Pseudonymisation Techniques and Best Practices* | Technique catalogue and recommendations. <https://www.enisa.europa.eu/sites/default/files/publications/Guidelines%20on%20shaping%20technology%20according%20to%20GDPR%20provisions.pdf> |
| ENISA — *Data Pseudonymisation: Advanced Techniques & Use Cases* | Advanced techniques (HMAC, secret sharing). <https://www.enisa.europa.eu/sites/default/files/publications/ENISA%20Report%20-%20Data%20Pseudonymisation%20-%20Advanced%20Techniques%20and%20Use%20Cases.pdf> |
| EDPS / AEPD — *Hash function as personal data pseudonymisation technique* | Why plain hashing of small input spaces is insufficient. <https://www.edps.europa.eu/sites/default/files/publication/19-10-30_aepd-edps_paper_hash_final_en.pdf> |
| NIST SP 800-188 | De-identification of government datasets; governance framing. <https://csrc.nist.gov/pubs/sp/800/188/final> |
| NIST SP 800-107 Rev. 1 | Hash truncation rationale (collision resistance halved). <https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-107r1.pdf> |
| NIST FIPS 180-4 | SHA-256 specification. <https://csrc.nist.gov/pubs/fips/180-4/upd1/final> |
| IETF RFC 2104 | HMAC construction. <https://www.rfc-editor.org/rfc/rfc2104> |

## Requirements satisfied

| Requirement | How we satisfy it | Source |
|---|---|---|
| Identifier replacement | `<TYPE:hash>` tokens via HMAC-SHA256; deterministic across runs. | GDPR Art. 4(5) |
| Additional information held separately | HMAC key and mapping file kept outside `<out_dir>`; exit `7` aborts `apply` if `--mapping` resolves under `<out_dir>`. | GDPR Art. 4(5); EDPB 01/2025 §3.2 |
| HMAC over plain hash | Per-installation secret key — without it, recovering plaintext from a token requires breaking SHA-256. Plain hash over a closed input space is brute-forceable in seconds. | EDPS hash paper; EDPB 01/2025; RFC 2104 |
| Cross-context unlinkability | Per-type key namespacing — same string in different fields produces different tokens. | ENISA Advanced |
| Truncation rationale | 128-bit truncation gives 64-bit collision resistance; safe to ≥ 10¹⁵ tokens. Math in [HASHING.md §6](HASHING.md#6-truncation). | NIST SP 800-107r1 |
| Auditability | JSONL report per run captures every substitution; retained alongside mapping under same access controls. Schema: [ARCHITECTURE.md → Report Schema](ARCHITECTURE.md#report-schema-jsonl). | NIST SP 800-188 |
| Reversibility under control | Mapping enables authorized reverse. Discarding key **and** mapping makes the output permanently de-identified. | — |

Construction, canonicalization, and the full design rationale: [HASHING.md](HASHING.md).

## What we do **not** claim

- **Anonymization.** Tokenized output is still personal data.
- **Detection completeness.** Literal + structured detection is high-precision but recall is bounded by the term list and regex patterns. NER is best-effort and explicitly flagged as a discovery aid, not a guarantee (consistent with ENISA Advanced §2.1).
- **Resistance to linkage attacks.** A determined adversary with auxiliary data can re-identify individuals from quasi-identifiers (writing style, timestamps, metadata) that this tool does not touch.
- **Memory or stream safety against side channels.** The HMAC key sits in process memory during a run.
- **Compliance certification.** This document maps design to standards; an external auditor must certify use in any specific regulated context.

## Operator obligations

See [SECURITY.md → Operational rules](SECURITY.md#operational-rules-enforced-or-recommended) for the normative list (what's tool-enforced vs operator-recommended). The compliance posture above assumes the operator follows that list.
