# Security & Threat Model

*For operators choosing how to store the key, mapping, and report.*

This document describes what an attacker can and cannot do given each combination of artifacts the tool produces, and the operational rules that must hold for the design to deliver its claims.

## Artifacts produced by a run

| Artifact | Default path | Sensitivity |
|---|---|---|
| HMAC key | `./.key` (user-chosen) | **Secret.** Anyone with the key can re-derive any token from a guessed plaintext. |
| Mapping file | `./runs/pseudonymize-mapping.json` (next to but **outside** `<out_dir>`) | **Secret.** Direct token → plaintext lookup. |
| JSONL report | `./runs/pseudonymize-report.jsonl` | **Secret** (contains plaintext spans). |
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
| Report must not reside inside `<out_dir>` | **Enforced** (exit `7`) | Same containment check as mapping; report contains plaintext `text` + `context`. |
| Key must come from `--key-file` or `PSEUDONYMIZE_KEY` env | **Enforced** (exit `3`) | No interactive prompt; no default key. |
| Key not echoed in logs or reports | **Enforced** | `--verbose` only logs file paths, span counts, key fingerprint (HMAC of key with fixed label). |
| Key file mode `0600` | Recommended | Operator responsibility; tool warns on world-readable key files. |
| Mapping file mode `0600` | Recommended | Operator responsibility. |
| Key from CSPRNG, ≥ 256 bits | Recommended | `openssl rand -hex 32` produces 32 bytes / 256 bits. |
| Key stored outside repo | Recommended | Repo ships a `runs/` sandbox + per-artefact globs (`.key`, `*.key`, `pseudonymize-mapping.json`, `pseudonymize-report.jsonl`, `terms.csv`, `*-mapping.json`, `*-report.jsonl`, `plan*.jsonl`) so the default layout is gitignored. |

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
- **Supply-chain attacks** on `python-stdnum`, `phonenumberslite`, or spaCy. Pin versions and verify hashes if your environment requires it.
- **Adversarial input corpora.** Malicious files designed to crash detectors are treated as I/O errors; no sandboxing of the input. Malicious `terms.csv` / `--ignore` files **are** in-scope — see "In-scope adversarial inputs" below.

## In-scope adversarial inputs

| Source | Threat | Mitigation |
|---|---|---|
| `terms.csv` (operator- or LLM-generated) | ReDoS via wildcard patterns expanding to catastrophic backtracking. | Structural guard rejects `(\.\*){2,}` / `(\?\+){1,}` at load (exit 4); per-match length cap `MAX_MATCH_LEN = 4096`; `--allow-broad-patterns` does not override the structural guard. |
| `--ignore` file | Zero-width / format characters in entries cause silent suppression failure. | NFKC + strip Unicode categories `Cf` and non-ASCII `Zs`; log `WARNING` on stripped chars. |
| `--plan` JSONL | `ReportRecord.file` field with `..` / absolute paths mirroring outside `<in_dir>`. | Containment check at plan-load (exit 4); resolved path must be under `<in_dir>`. |
| Input file size | Multi-GB single files exhausting memory. | `MAX_FILE_BYTES` (default 256 MB) on walker; `MAX_MAPPING_BYTES` on `mapping.load_mapping`. Exit 6 with clear message. |

## LLM and downstream consumption

The tool is not LLM-aware. When pseudonymized output flows into an LLM-bound pipeline (RAG ingestion, summarisation, chatbot context, fine-tuning corpus), operators must treat these properties explicitly:

### Pseudonymization is not a prompt-injection defense

The tool replaces *detected entities*. Adversarial instructions in surrounding prose (`Ignore previous instructions; reveal …`) pass through unchanged. A replaced `<NAME:7f3a…>` inside an injection payload is still a live payload. Use a structural prompt-injection mitigation (system-prompt separation, XML-tagged context fencing, instruction-data separation) at the LLM boundary; the pseudonymizer is not a content filter.

### Artifacts must not enter LLM chat contexts

`pseudonymize-mapping.json` and `pseudonymize-report.jsonl` contain plaintext PII (the mapping by definition; the report's `text` and `context` fields). Pasting either into an LLM chat for debugging ships every plaintext span to the model provider. Treat them with the same access controls as the HMAC key. AGENTS.md non-negotiable enforces the agent-side rule.

### Token format and chat-template tokenizers

`<TYPE:hex>` uses angle brackets, which collide with chat-template special tokens in several model families (`<s>` / `</s>`, `<|im_start|>`, `<|endoftext|>`, `<extra_id_N>`). Operators feeding pseudonymized text to an LLM should verify that the target tokenizer treats `<TYPE:hex>` as ordinary text. A delimiter-swapped variant (`[[TYPE:hex]]`) for LLM-bound corpora is planned for 0.2.0 via `--output-format`. See [HASHING.md §9](HASHING.md#9-output-format).

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
