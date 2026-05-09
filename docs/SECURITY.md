# Security & Threat Model

*For operators choosing how to store the key, mapping, and report.*

This document describes what an attacker can and cannot do given each combination of artifacts the tool produces, and the operational rules that must hold for the design to deliver its claims.

## Artifacts produced by a run

| Artifact | Default path | Sensitivity |
|---|---|---|
| HMAC key | `./.key` (user-chosen) | **Secret.** Anyone with the key can re-derive any token from a guessed plaintext. |
| Mapping file | `./pseudonymize-mapping.json` (next to but **outside** `<out_dir>`) | **Secret.** Direct token → plaintext lookup. |
| JSONL report | `./pseudonymize-report.jsonl` | **Secret** (contains plaintext spans). |
| Term list | `--terms FILE` | **Secret** (lists every sensitive value the operator chose to pseudonymize). |
| Mirrored output | `<out_dir>/` | **Distributable** under the operator's release process. |

## Adversary capabilities by artifact possession

| Adversary holds | Can recover plaintext? | How |
|---|---|---|
| Output only | No (within HMAC strength) | Brute force requires guessing both key and value. |
| Output + term list | Partial — only entries in the term list | Recompute candidate tokens; match against output. **Mitigation: keep the term list secret.** |
| Output + key | Same as above; can additionally test arbitrary guesses | Compute `HMAC(key, guess)`; match. Not feasible for unbounded plaintext space, trivial for closed lists. |
| Output + mapping | Yes (full reverse) | Direct lookup. |
| Output + key + mapping | Yes | Either path. |

The design assumes the operator can keep at least the **mapping** (or the **key + term list** combination) confidential. Loss of the mapping is the dominant risk.

## Operational rules (enforced or recommended)

| Rule | Enforced by tool? | Notes |
|---|---|---|
| Mapping must not reside inside `<out_dir>` | **Enforced** (exit `7`) | Path is canonicalized and checked. |
| Key must come from `--key-file` or `PSEUDONYMIZE_KEY` env | **Enforced** (exit `3`) | No interactive prompt; no default key. |
| Key not echoed in logs or reports | **Enforced** | `--verbose` only logs file paths, span counts, key fingerprint (HMAC of key with fixed label). |
| Key file mode `0600` | Recommended | Operator responsibility; tool warns on world-readable key files. |
| Mapping file mode `0600` | Recommended | Operator responsibility. |
| Key from CSPRNG, ≥ 256 bits | Recommended | `openssl rand -hex 32` produces 32 bytes / 256 bits. |
| Key stored outside repo | Recommended | Add `.key`, `*.key`, `pseudonymize-mapping.json`, `pseudonymize-report.jsonl` to `.gitignore`. |

## Cryptographic choices

| Choice | Value | Rationale |
|---|---|---|
| MAC | HMAC-SHA256 | RFC 2104; FIPS 180-4. <https://www.rfc-editor.org/rfc/rfc2104> · <https://csrc.nist.gov/pubs/fips/180-4/upd1/final> |
| Key length | 256 bits (32 bytes) | Matches HMAC-SHA256 block-aligned key; full output entropy. |
| Per-type key namespacing | `key \|\| ":" \|\| type` | Prevents cross-field token correlation (ENISA Advanced §3.4). |
| Truncation | 128 bits (32 hex) | NIST SP 800-107r1 §5.1: 64-bit collision resistance, sufficient for ≤10⁷ tokens. <https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-107r1.pdf> |
| KDF for the secret | None (raw key) | The input space is not a password; HMAC's keyed PRF property is what we need. |

We deliberately do **not** use bcrypt/argon2/PBKDF2: those defend against guessing a low-entropy password. Our threat is recovery of a plaintext from a token; the relevant defense is HMAC key secrecy plus enough output bits.

Full token design rationale (canonicalization, `kind` namespacing, alternatives considered, stability matrix, dependency-stability commitment): [HASHING.md](HASHING.md).

## Out-of-scope threats

- **Side channels** (memory dumps, swap, core files). Use a host with disabled core dumps and encrypted swap when handling regulated data.
- **Compromised host running the tool.** A root-level compromise during a run defeats every protection.
- **Linkage from quasi-identifiers** the tool does not touch (writing style, timestamps, document metadata, image EXIF). Tokenizing names does not anonymize a document whose timestamps and rare phrases uniquely identify the author.
- **Adversarial input.** Malicious files designed to crash detectors are treated as I/O errors; no sandboxing of the input.
- **Supply-chain attacks** on `python-stdnum`, `phonenumberslite`, or spaCy. Pin versions and verify hashes if your environment requires it.

## Reverse lookup

For 0.1.0, reverse lookup is a `jq` one-liner against the JSON mapping:

```bash
jq -r '.["<NAME:7f3a9c8b…>"].value' pseudonymize-mapping.json
```

A `pseudonymize reverse` subcommand is planned for 1.0.0 (see [roadmap](roadmap.md)).

## Permanent de-identification

To make output computationally irreversible:

1. Distribute `<out_dir>/` as needed.
2. Securely delete the **mapping file** *and* the **HMAC key**.
3. Retain the JSONL report only if it does not contain plaintext spans you wish to forget; otherwise destroy it as well.

After step 2, no party — including the original operator — can recover plaintext from a token without breaking SHA-256.

## Key rotation (procedure)

Rotation tooling is deferred to 1.0.0. For 0.1.0, the manual procedure is:

1. Generate a new key.
2. Re-run `pseudonymize apply` against the **plaintext source** (not the previously tokenized output) using the new key.
3. Produce a new mapping file.
4. Distribute new output + retire old output and old mapping.

Re-tokenizing already-tokenized output is **not** supported; tokens must always derive from plaintext.

## Reporting issues

(TBD: security contact email / GPG key.)
