# Hashing

*For implementers and auditors who need to know exactly what the token derivation guarantees.*

Construction, input canonicalization, namespacing, and stability of the hash-derived tokens this tool produces. This is the canonical reference for all token-related design choices; other docs link here for the "why".

> **Scope note.** "Hashing" here covers the input canonicalization pipeline as well as the keyed-MAC step that follows it. Both are inseparable parts of the token contract.

---

## 1. Construction

```text
token = "<" + TYPE + ":" + hex(HMAC-SHA256(K, M)[:16]) + ">"

where:
  TYPE ∈ {NAME, EMAIL, PHONE, IBAN, CC, SSN, ORG, LOC, NPI, DEA, VIN}
  K    = secret_key || ":" || lowercase(TYPE)
  M    = kind || ":" || subject
  kind ∈ {"id", "v"}
  subject = group_id_string                 if the row has an `id`
            canonical(matched_text, type)   otherwise
```

`hex(...)` is lowercase. Truncation is the **first 16 bytes** of the MAC output (128 bits → 32 hex chars).

References:

- HMAC: [RFC 2104](https://www.rfc-editor.org/rfc/rfc2104)
- SHA-256: [NIST FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)
- Truncation rationale: [NIST SP 800-107r1 §5.1](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-107r1.pdf)

### Worked example

For implementers writing parity tests. UTF-8 encoding for both `K` and `M`.

| Input | Value |
|---|---|
| `secret_key` | `test-key` |
| `TYPE` | `NAME` |
| `K` | `test-key:name` |

| `kind` | `subject` | `M` | Expected token |
|---|---|---|---|
| `id` | `p1` | `id:p1` | `<NAME:d273039bdb37a853c53f592bb1b460e0>` |
| `v` | `john doe` | `v:john doe` | `<NAME:003e28a1b30fc476e898352263414f11>` |

The `v`-kind subject `john doe` is the canonical form of the surface string `John Doe` for type `name` (NFKC + `str.casefold()`; see §2).

---

## 2. Per-type canonicalization

Hashing the surface form would make `Alice`, `ALICE`, and `alice` produce three different tokens — directly contradicting determinism. We instead hash a per-type **canonical form**, then store the *original* surface form in the mapping `value` field for human-readable reverse lookup.

| Type | Canonical form | Why |
|---|---|---|
| `name`, `org`, `loc` | NFKC normalize → `str.casefold()` | Case + Unicode folding (e.g. `ß` → `ss`, `ﬁ` → `fi`). Same person across documents → same token. |
| `email` | NFKC → lowercase entire address | RFC 5321 says local-part is case-sensitive; in practice all major providers treat it case-insensitively, so we do too. Avoids `Alice@x.com` ≠ `alice@x.com` failure mode. |
| `phone` | E.164 (`+CC...`) via `phonenumberslite` | `+49 30 1234567`, `030 1234567` (with default region), `+49-30-1234-567` all collapse to one token. |
| `iban` | strip whitespace; uppercase | ISO 13616: `DE89 3704 0044 0532 0130 00` and `de89370400440532013000` are the same IBAN. |
| `cc` | digits only | `4111-1111-1111-1111` and `4111111111111111` are the same card. |
| `ssn` | digits only | Same as CC. |
| `npi` | digits only | NPI is 10 digits; same provider ID across documents → same token. |
| `dea` | strip whitespace; uppercase | DEA is 2 letters + 7 digits; folds incidental case. |
| `vin` | strip whitespace; uppercase | VINs are uppercase per ISO 3779; folds incidental case. |

`canonical()` is deterministic: it never changes its output for the same input within a major version of this tool. See §8 (Dependency stability).

---

## 3. The `kind` prefix

The MAC message is `kind || ":" || subject` where `kind` is `"id"` or `"v"`. The prefix prevents an `id`-grouped subject and a raw value subject from colliding when they happen to share a string. Example: `id="doe"` grouping variants of person Doe, plus a separate value-row whose canonical is also `doe` — without the prefix both would hash to `HMAC(K, "doe")` and produce the same token.

The colon is a hard delimiter: `":"` is forbidden in `kind` (only `id` and `v` are legal), so a value subject that happens to start with `id:` becomes `b"v:id:p1"` — distinct from `b"id:p1"`. This is hygiene, not defense — an attacker who can write `terms.csv` already controls pseudonymization. The real value is preventing accidental confusion.

---

## 4. Why hash the `id` string (Design A)

For a row with an `id`, the MAC subject is the literal `id` string the operator typed. Three alternatives were considered.

| Design | `subject` for grouped row | Stable when you… | Breaks when you… |
|---|---|---|---|
| **A — hash the `id` (chosen)** | `id_string` | add/remove variants from the group | rename the `id` |
| B — hash a content-derived canonical (e.g. lex-min of all variants in the group) | `min(canonicals)` | rename the `id` | add/remove the variant that is the lex-min |
| C — hash the sorted set of all canonicals | `"\x00".join(sorted(canonicals))` | nothing | any add/remove of any variant |
| D — registration-time frozen synthetic id | per-group UUID stored in mapping at first run | both rename and add/remove | losing the mapping (mapping becomes load-bearing for token derivation) |

### Why A wins

- **Transparent failure mode.** "Don't rename `id` strings" is a one-line operator rule. B and C have hidden failure modes (a junior teammate adding a variant changes tokens silently under B; under C any churn does).
- **Variant churn is the common case.** Operators routinely discover a missed alias for an existing entity. A is invariant to this.
- **No state across runs.** D requires a registration database (a stateful first-write that subsequent runs must respect). A is stateless.
- **`id` rename is recoverable** through the standard re-tokenize-from-plaintext path (see §11). Hidden token shifts under B/C are harder to detect after the fact.

### When to revisit

Move to D (frozen synthetic id) if operators routinely rename `id` strings. Move to B if term lists from independent teams need to be merged without coordinating namespaces. Neither is the v1 case.

---

## 5. Determinism without salt

The tool produces the **same token for the same input**, every run, every machine that holds the same key. There is no per-record random salt.

This is intentional, not an oversight:

- **A random salt would destroy the only useful property** of pseudonymization at this layer — the ability to join across documents (e.g. "Alice appears in 47 logs"). Random salt → 47 different tokens → no join.
- **The HMAC key plays the role of a "global salt"**, drawn once per installation and held secret. Brute force requires the key, not just the algorithm. HMAC-with-secret-key is endorsed as a valid pseudonymization technique by [ENISA — Data Pseudonymisation: Advanced Techniques & Use Cases](https://www.enisa.europa.eu/sites/default/files/publications/ENISA%20Report%20-%20Data%20Pseudonymisation%20-%20Advanced%20Techniques%20and%20Use%20Cases.pdf).
- **No KDF (bcrypt/argon2/PBKDF2)** is applied to the key. Those defend against guessing a *low-entropy password*. Our threat is recovery of a plaintext from a token; the relevant defense is HMAC key secrecy and sufficient output bits, not CPU-hardening.

If you ever want non-deterministic output (each occurrence gets a unique token, breaking joins), this is **not** the right tool — that is a different design (envelope encryption with random IVs).

---

## 6. Truncation

We truncate HMAC-SHA256 to **128 bits** (16 bytes, 32 hex chars).

| Property | Value |
|---|---|
| MAC output | 256 bits |
| Truncated output | 128 bits |
| Output space *N* | 2¹²⁸ ≈ 3.4 × 10³⁸ |
| Collision resistance ([SP 800-107r1 §5.1](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-107r1.pdf)) | 64 bits (≈ 1.8 × 10¹⁹ tokens for 50% birthday-collision probability) |

Birthday-collision probability for *n* random tokens is approximately *n²* / (2*N*) = *n²* / 2¹²⁹:

| Corpus size *n* | P(any collision) |
|---|---|
| 10⁶ | ≈ 1.5 × 10⁻²⁷ |
| 10⁹ | ≈ 1.5 × 10⁻²¹ |
| 10¹² | ≈ 1.5 × 10⁻¹⁵ |
| 10¹⁵ | ≈ 1.5 × 10⁻⁹ |
| 10¹⁸ | ≈ 1.5 × 10⁻³ (~0.15%) |

128 bits is the floor. Below 96 bits, collision probability becomes a concern at corpus scale; above 128 bits, tokens become noisy in plain text without buying meaningful additional resistance for any realistic corpus.

If your corpus exceeds ~10¹⁵ tokens, raise the truncation length (a v1.1 flag) rather than living with the collision risk.

---

## 7. Operator stability matrix

What does and does not preserve token values:

| Operator action | Token unchanged? | Notes |
|---|---|---|
| Add a new variant to an existing `id` group | ✅ | Token depends only on `id` string. |
| Remove a variant from an existing `id` group | ✅ | Same. |
| Reorder rows in `terms.csv` | ✅ | Order doesn't enter the MAC. |
| Add a brand-new entity (new `id`) | ✅ | Existing tokens unaffected. |
| Mix literals and patterns under the same `id` | ✅ | All collapse to the group token. |
| Change letter case in a value (without `id`) | ✅ | Canonicalization handles it. |
| Reformat a phone/IBAN (spaces, dashes, country code) | ✅ | Canonicalization handles it. |
| Re-run with the same key + terms + plaintext source | ✅ | Determinism guarantee. |
| Add a new variant **without** an `id` | ❌ for that variant; ✅ for unrelated entities | New variant gets its own token. |
| Change the `type` of a row | ❌ | Different namespace (`K` includes `type`). |
| Rename an `id` string | ❌ | Token derives from `id`. |
| Rotate the HMAC key | ❌ | Intentional — see [SECURITY.md → Key rotation](SECURITY.md#key-rotation-procedure). |
| Switch tool major version | ❌ unless release notes say otherwise | Canonicalization rules may evolve across majors. |
| Switch `python-stdnum` / `phonenumberslite` versions | ⚠️ | Canonical-to-token mapping unchanged, but **detection set may shift** (newly valid IBANs, re-classified phone numbers). See §8. |
| Upgrade Python minor version | ⚠️ | ASCII inputs unaffected; unusual Unicode may shift (NFKC tables track the interpreter's Unicode version). See §8. |

---

## 8. Dependency-stability commitment

Within a tool major version, the canonical-to-token mapping is locked. `canonical(text, type)` is implemented in-tree; third-party libraries are used only for detection and validation, never to feed the hash directly. `phonenumbers.parse(...).national_number` and `python-stdnum.iban.is_valid` are read out, then we format / normalize ourselves with fixed rules. Upstream formatting-default changes do not affect tokens.

Three things are **not** locked and can drift:

- **Detection drift.** A `python-stdnum` upgrade that fixes `iban.is_valid` (or adds a country code) shifts which strings get detected — and therefore tokenized — even though the canonical-to-token mapping itself is stable.
- **Phone parsing drift.** A `phonenumbers` upgrade that re-classifies a number's country code or changes which digit sequences parse will change `national_number` and therefore the token. Pin `phonenumbers` minor versions; review release notes before bumping.
- **Python Unicode tables.** `unicodedata.normalize('NFKC', ...)` and `str.casefold()` use the interpreter's bundled Unicode tables. A Python release that bumps the Unicode standard version (e.g. 15.1 → 16.0) can shift the canonical form of newly-introduced or revised codepoints. ASCII-only inputs are unaffected; general Unicode is a low-frequency but real drift source. Pin Python minor version in deployment to bound this.

Deliberate canonicalization changes go in a tool major-version bump with a documented migration; patch and minor releases never alter `canonical()`.

---

## 9. Output format

The token format is `<TYPE:hex>`, e.g. `<NAME:7f3a9c8b2e44d913…>`. Three alternatives were considered:

| Format | Pros | Cons | Verdict |
|---|---|---|---|
| `<NAME:7f3a9c8b…>` (chosen) | Greppable. Type visible at a glance. Length predictable (37 chars for `CC`, 38 for `ORG`, 39 for `NAME`/`LOC`/`SSN`, 40 for `EMAIL`/`PHONE`/`IBAN` — formula is `len(TYPE) + 35`). Distinct from any natural text. | Slightly longer than alternatives. | ✅ |
| `[NAME_1]`, `[NAME_2]` | Short, human-readable. | Per-document counter destroys cross-document joins; counter requires state. | ✗ |
| Base64 (`<NAME:fzqcsi5E…>`) | 22 chars instead of 32. | Case-sensitive grep; `+` and `/` need escaping in some contexts (URLs, regex). | ✗ |
| Raw hex without delimiters | Shortest. | Indistinguishable from natural hex content (commit hashes, ETags); no type visible. | ✗ |

The angle brackets are deliberate: they are uncommon in natural text, easy to grep (`<NAME:`), easy to detect for un-pseudonymization tooling, and parse cleanly in JSON/CSV/YAML when escaped or quoted by the host format.

**Caveat for LLM-bound corpora.** Several chat-template tokenizers reserve angle-bracket sequences as special tokens — `<s>` / `</s>` (Llama), `<|im_start|>` / `<|endoftext|>` (ChatML, GPT-style), `<extra_id_N>` (T5). Feeding `<TYPE:hex>` text through such a tokenizer may yield surprising splits or trigger control-sequence behaviour. Operators bound for an LLM pipeline should verify the target tokenizer treats `<TYPE:hex>` as ordinary text; a delimiter-swapped output mode (e.g. `[[TYPE:hex]]`) is planned for 0.2.0 via `--output-format` — see [roadmap.md](roadmap.md). The on-disk format inside this repo remains `<TYPE:hex>`; the swap happens at the report/output boundary, not at the token-construction boundary, so HMAC stability is preserved.

---

## 10. Mapping file schema (normative)

The mapping is a JSON object — top-level keys are tokens, values are records.

```json
{
  "<NAME:7f3a9c8b2e44d913…>": {
    "value":        "John Doe",
    "canonical":    "john doe",
    "type":         "name",
    "id":           "p1",
    "first_seen":   "2026-05-10T14:32:11Z",
    "last_seen":    "2026-05-10T14:32:11Z",
    "occurrences":  47
  },
  "<EMAIL:1c4d22e9…>": {
    "value":        "Bob.Smith@Example.com",
    "canonical":    "bob.smith@example.com",
    "type":         "email",
    "id":           null,
    "first_seen":   "2026-05-10T14:32:12Z",
    "last_seen":    "2026-05-10T14:32:12Z",
    "occurrences":  3
  }
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `value` | string | yes | First surface form encountered. Used for human-readable reverse. |
| `canonical` | string | yes | The exact `subject` that was hashed. Allows a verifier to recompute the token. |
| `type` | string | yes | Lowercase entity type. |
| `id` | string \| null | yes | Group `id` if any, else `null`. |
| `first_seen` | RFC 3339 timestamp | yes | When this token was first added to the mapping. Preserved across runs. |
| `last_seen` | RFC 3339 timestamp | yes | Updated to the start time of the most recent run that produced this token. |
| `occurrences` | integer | yes | **Cumulative** count of substitutions across all `apply` runs that have written this mapping file. |

### Persistence semantics across runs

The mapping is **append-with-update**: an `apply` run loads the existing mapping (if present), then for each token produced this run:

- New token → insert with `first_seen = last_seen = run_start`, `occurrences = run_count`.
- Existing token → keep `first_seen`; set `last_seen = run_start`; add `run_count` to `occurrences`.
- Token in mapping but not produced this run → left untouched (entry preserved; counters not modified).

The mapping is rewritten atomically (`tmp` file → `rename`) at the end of the run. Concurrent `apply` runs against the same mapping path are **not supported** (no file locking; last writer wins and may lose intermediate state).

For a fresh count (e.g. switching corpora), point `--mapping` at a new file or delete the existing one first.

---

## 11. Re-tokenization is not supported

Tokens always derive from **plaintext**. For any change that shifts tokens (key rotation, `id` rename, type change, major-version migration): re-run `pseudonymize apply` against the plaintext source with the new key/terms; distribute the new output; retire the old.

Re-tokenizing from the mapping is mechanically easy but operationally wrong — it puts key rotation in the mapping holder's hands, coupling cadence to their availability and concentrating compromise risk. The plaintext path keeps the trust boundary clean: corpus owner rotates, mapping holder verifies.

---

## See also

- Construction summary: [ARCHITECTURE.md → Token Format](ARCHITECTURE.md#token-format)
- Regulatory mapping: [COMPLIANCE.md](COMPLIANCE.md)
- Threat model and key handling: [SECURITY.md](SECURITY.md)
- Term-list schema and `id` semantics: [TERMS_CSV.md](TERMS_CSV.md)
