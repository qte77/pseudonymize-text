# Hashing

Construction, input canonicalization, namespacing, and stability of the hash-derived tokens this tool produces. This is the canonical reference for all token-related design choices; other docs link here for the "why".

> **Scope note.** "Hashing" here covers the input canonicalization pipeline as well as the keyed-MAC step that follows it. Both are inseparable parts of the token contract.

---

## 1. Construction

```
token = "<" + TYPE + ":" + hex(HMAC-SHA256(K, M)[:16]) + ">"

where:
  TYPE ∈ {NAME, EMAIL, PHONE, IBAN, CC, SSN, ORG, LOC}
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

`canonical()` is deterministic: it never changes its output for the same input within a major version of this tool. See §8 (Dependency stability).

---

## 3. The `kind` prefix

The MAC message is `kind || ":" || subject` where `kind` is `"id"` or `"v"`. This prefix exists to prevent a **construction collision** between an `id`-grouped row and a normal value row.

### The attack it prevents

Without the prefix, the MAC inputs would be just the `id` string or the canonical value. An adversary who controls `terms.csv` (or who can guess what's in it) could:

1. Observe that some operator uses `id="p1"` for a high-value entity (Alice).
2. Add an unrelated row to a future term list: `value=p1, type=name`.
3. After canonicalization (`p1` → `p1`), this row would produce the **same** token as Alice's group.
4. Adversary now has token confusion across the corpus.

With the `kind` prefix, the MAC inputs become `b"id:p1"` vs `b"v:p1"`, which are different inputs and produce different MACs. No matter what value the adversary inserts, it cannot collide with any `id`-derived token.

### Why the colon

`":"` is forbidden in `kind` (the only legal values are `id` and `v`), so prefix-extension attacks like a value of `id:p1` collapsing to `b"v:id:p1"` ≠ `b"id:p1"` cannot collide either. The colon is a hard delimiter.

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
- **The HMAC key plays the role of a "global salt"**, drawn once per installation and held secret. Brute force requires the key, not just the algorithm. This is the construction recommended by [ENISA Advanced Pseudonymisation §3](https://www.enisa.europa.eu/sites/default/files/publications/ENISA%20Report%20-%20Data%20Pseudonymisation%20-%20Advanced%20Techniques%20and%20Use%20Cases.pdf).
- **No KDF (bcrypt/argon2/PBKDF2)** is applied to the key. Those defend against guessing a *low-entropy password*. Our threat is recovery of a plaintext from a token; the relevant defense is HMAC key secrecy and sufficient output bits, not CPU-hardening.

If you ever want non-deterministic output (each occurrence gets a unique token, breaking joins), this is **not** the right tool — that is a different design (envelope encryption with random IVs).

---

## 6. Truncation

We truncate HMAC-SHA256 to **128 bits** (16 bytes, 32 hex chars).

| Property | Value |
|---|---|
| MAC output | 256 bits |
| Truncated output | 128 bits |
| Collision resistance ([SP 800-107r1 §5.1](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-107r1.pdf)) | 64 bits |
| Birthday-collision probability over 10⁶ tokens | ≈ 2.7 × 10⁻¹² |
| Birthday-collision probability over 10⁷ tokens | ≈ 2.7 × 10⁻¹⁰ |
| Birthday-collision probability over 10⁹ tokens | ≈ 2.7 × 10⁻⁶ |

128 bits is the floor. Below 96 bits, collision probability becomes a real concern at corpus scale. Above 128 bits, tokens become noisy in plain text without buying meaningful collision resistance for any realistic corpus.

If your corpus exceeds ~10⁸ tokens, raise the truncation length (a v1.1 flag) rather than living with the collision risk.

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
| Switch `python-stdnum` / `phonenumberslite` versions | ✅ within a tool major version | See §8. |

---

## 8. Dependency-stability commitment

Token stability across third-party library upgrades is a **first-class guarantee** within a tool major version. The implementation rule:

- All `canonical(text, type)` logic is implemented in-tree.
- Third-party libraries (`python-stdnum`, `phonenumberslite`, spaCy) are used **only for detection and validation**, not for normalization that feeds the hash.

Concretely:

- We use `phonenumbers.parse(text, default_region).national_number` to extract digits, then format E.164 ourselves with a fixed format string. Future `phonenumbers` releases that change formatting defaults do not affect tokens.
- We use `python-stdnum.iban.is_valid` for validation, then strip whitespace and uppercase ourselves. Future `stdnum` normalize-fn changes do not affect tokens.
- spaCy NER is detection-only; the canonical it feeds into the hash is our `canonical(text, type)`, not anything spaCy returns.

If a canonicalization rule ever needs to change (Unicode normalization tightens, regulatory body revises a format), it goes in a tool major-version bump with a documented migration path. Patch and minor releases never alter token output.

---

## 9. Output format

The token format is `<TYPE:hex>`, e.g. `<NAME:7f3a9c8b2e44d913…>`. Three alternatives were considered:

| Format | Pros | Cons | Verdict |
|---|---|---|---|
| `<NAME:7f3a9c8b…>` (chosen) | Greppable. Type visible at a glance. Length predictable (38 chars for `NAME`, 39 for `EMAIL`, etc.). Distinct from any natural text. | Slightly longer than alternatives. | ✅ |
| `[NAME_1]`, `[NAME_2]` | Short, human-readable. | Per-document counter destroys cross-document joins; counter requires state. | ✗ |
| Base64 (`<NAME:fzqcsi5E…>`) | 22 chars instead of 32. | Case-sensitive grep; `+` and `/` need escaping in some contexts (URLs, regex). | ✗ |
| Raw hex without delimiters | Shortest. | Indistinguishable from natural hex content (commit hashes, ETags); no type visible. | ✗ |

The angle brackets are deliberate: they are uncommon in natural text, easy to grep (`<NAME:`), easy to detect for un-pseudonymization tooling, and parse cleanly in JSON/CSV/YAML when escaped or quoted by the host format.

---

## 10. Mapping file schema (normative)

The mapping is a JSON object — top-level keys are tokens, values are records.

```json
{
  "<NAME:7f3a9c8b2e44d913…>": {
    "value":        "Alice Müller",
    "canonical":    "alice müller",
    "type":         "name",
    "id":           "p1",
    "first_seen":   "2026-05-10T14:32:11Z",
    "occurrences":  47
  },
  "<EMAIL:1c4d22e9…>": {
    "value":        "Bob.Smith@Example.com",
    "canonical":    "bob.smith@example.com",
    "type":         "email",
    "id":           null,
    "first_seen":   "2026-05-10T14:32:12Z",
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
| `first_seen` | RFC 3339 timestamp | yes | When this token was first added to the mapping. |
| `occurrences` | integer | yes | Total occurrences across the apply run that produced this mapping. |

Subsequent surface forms of the same entity (e.g. `Alice` and `ALICE` both mapping to `<NAME:7f3a…>`) do not create new entries; they bump `occurrences`. The `value` field captures whichever surface form was seen first.

The mapping is rewritten atomically (`tmp` file → `rename`) at the end of an `apply` run. Concurrent runs against the same mapping path are not supported.

---

## 11. Re-tokenization is not supported

Tokens always derive from **plaintext**. There is no supported path that takes already-tokenized output and produces different tokens (e.g. for key rotation or `id` renaming).

The supported recovery path for any change that shifts tokens (key rotation, `id` rename, type change, major-version migration) is:

1. Retain the **plaintext source**.
2. Re-run `pseudonymize apply` with the new key / terms / version.
3. Distribute the new output; retire the old output and old mapping.

This rule exists because re-tokenizing from existing tokens would require either (a) reversing the tokens via the mapping (defeats the point) or (b) re-detecting in tokenized output (unreliable and creates forensic gaps). Both options weaken the compliance posture.

---

## See also

- Construction summary: [ARCHITECTURE.md → Token Format](ARCHITECTURE.md#token-format)
- Regulatory mapping: [COMPLIANCE.md](COMPLIANCE.md)
- Threat model and key handling: [SECURITY.md](SECURITY.md)
- Term-list schema and `id` semantics: [TERMS_CSV.md](TERMS_CSV.md)
