# Compliance Posture

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

### 1. Identifier replacement (GDPR Art. 4(5))

Sensitive surface strings are replaced by `<TYPE:hash>` tokens computed by HMAC-SHA256. Same input + same key → same token (deterministic), enabling joins across documents while breaking direct attribution.

### 2. Additional information held separately (GDPR Art. 4(5); EDPB 01/2025 §3.2)

Two separable secrets are required to attribute a token to a person:

- the **HMAC key** (recompute the token from a guess), and
- the **mapping file** (look up the plaintext directly).

By contract, neither resides inside the output tree. Exit code `7` aborts `apply` if `--mapping` resolves under `<out_dir>`.

### 3. HMAC over plain hash (EDPS hash paper, EDPB 01/2025 §4.1)

Plain SHA-256 over a closed input space (e.g. names from a finite list) is brute-forceable in seconds. We use HMAC-SHA256 with a per-installation secret key (RFC 2104 §2). Without the key, recovering plaintext from a token requires breaking SHA-256 collision resistance.

### 4. Cross-context unlinkability (ENISA Advanced §3.4)

The HMAC key is namespaced per entity type:

```text
token = "<" + TYPE + ":" + HMAC(key || ":" || type, kind || ":" || subject)[:16].hex() + ">"
```

where `kind` is `"id"` (group identifier) or `"v"` (canonical value). Full construction, canonicalization, and design rationale: [HASHING.md](HASHING.md).

The literal string `"acme"` appearing in a `name` field and an `org` field produces **different** tokens, preventing trivial cross-field linkage.

### 5. Truncation rationale (NIST SP 800-107r1 §5.1)

We truncate to 128 bits (32 hex chars). Per §5.1, truncating to λ bits gives λ/2 bits of collision resistance. 64 bits of collision resistance keeps birthday-collision probability over 10⁷ terms at ≈ 2.7 × 10⁻¹⁰ — negligible for any realistic corpus while keeping tokens compact.

### 6. Auditability (NIST SP 800-188 §4)

Every run produces a JSONL **report** (`detect`) or echoes one (`apply`). The report is the audit trail of what was substituted, with file path, character offsets, detector source, and (for NER) confidence. Operators are advised to retain the report alongside the mapping under the same access controls. Schema in [ARCHITECTURE.md → Report Schema](ARCHITECTURE.md#report-schema-jsonl).

### 7. Reversibility under control

The mapping file enables reverse lookup. To make output **permanently** de-identified, discard the HMAC key **and** the mapping file. Token re-derivation is then computationally infeasible.

## What we do **not** claim

- **Anonymization.** Tokenized output is still personal data.
- **Detection completeness.** Literal + structured detection is high-precision but recall is bounded by the term list and regex patterns. NER is best-effort and explicitly flagged as a discovery aid, not a guarantee (consistent with ENISA Advanced §2.1).
- **Resistance to linkage attacks.** A determined adversary with auxiliary data can re-identify individuals from quasi-identifiers (writing style, timestamps, metadata) that this tool does not touch.
- **Memory or stream safety against side channels.** The HMAC key sits in process memory during a run.
- **Compliance certification.** This document maps design to standards; an external auditor must certify use in any specific regulated context.

## Operator obligations

To preserve the compliance posture, the operator must:

1. Generate the HMAC key from a CSPRNG (`openssl rand -hex 32` or equivalent) and store it outside the data tree, with restrictive ACLs.
2. Store the mapping file outside the output tree, with the same or stricter ACLs as the original data.
3. Treat the JSONL report as confidential when it contains plaintext (it does, by construction).
4. Rotate the key on a documented schedule; record old-key/new-key transitions in change-management. (Tooling for rotation is deferred — see [ARCHITECTURE.md → What's deferred](ARCHITECTURE.md#whats-deferred).)
5. Review NER spans before first apply on a new corpus.

See [SECURITY.md](SECURITY.md) for the threat model that grounds these obligations.
