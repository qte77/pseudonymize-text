# Terms File Schema

The term list tells the **literal** and **pattern** detectors what to look for. Structured detectors (email, phone, IBAN, CC, SSN) and NER do not consult it.

Two formats are supported: CSV (recommended) and JSON.

## CSV

UTF-8, comma-delimited, header row required. Parsed with the Python stdlib [`csv`](https://docs.python.org/3/library/csv.html) module.

| Column | Required | Default | Allowed values |
|---|---|---|---|
| `value` | yes | — | Plaintext literal **or** wildcard pattern. |
| `type` | no | `name` | `name`, `email`, `phone`, `iban`, `cc`, `ssn`, `org`, `loc`. |
| `id` | no | — | Free-form group identifier. Rows sharing an `id` resolve to the **same** token. |

Extra columns are ignored.

### Example

```csv
id,value,type
p1,Alice Müller,name
p1,Müller Alice,name
p1,"Müller, Alice",name
p1,A. Müller,name
p1,alice.mueller@acme.com,email
p2,Bob Smith,name
,acme-corp,org
,*@acme.com,email
,12 Main St,loc
```

## JSON

UTF-8, top-level array of objects with the same field names:

```json
[
  {"id": "p1", "value": "Alice Müller", "type": "name"},
  {"id": "p1", "value": "Müller Alice", "type": "name"},
  {"value": "*@acme.com", "type": "email"}
]
```

## Type semantics

| Type | Match anchoring | Token prefix |
|---|---|---|
| `name` | `\b…\b` (Unicode word boundary) | `<NAME:…>` |
| `org` | `\b…\b` | `<ORG:…>` |
| `loc` | `\b…\b` | `<LOC:…>` |
| `email` | `\b…\b`, `@` allowed inside | `<EMAIL:…>` |
| `phone` | digits + separators, leading `+` allowed | `<PHONE:…>` |
| `iban` | letters+digits, no internal whitespace | `<IBAN:…>` |
| `cc` | digits + spaces/dashes | `<CC:…>` |
| `ssn` | digits + dashes | `<SSN:…>` |

Matching is case-insensitive (NFKC + casefold). Hashing uses a per-type **canonical form**, not the surface form, so `Alice` and `ALICE` produce the same token. The original surface form is preserved verbatim in the mapping `value` field. See [ARCHITECTURE.md → Canonicalization](ARCHITECTURE.md#canonicalization-canonicaltext-type).

## `id` grouping

Rows with the same `id` produce the **same** token. Use this to collapse known variants of one entity:

```csv
id,value,type
p1,Alice Müller,name
p1,Müller Alice,name
p1,A. Müller,name
```

All three surface forms → `<NAME:7f3a9c8b…>` because the token is `HMAC(key||":name", "id:p1")` for every row in the group, regardless of `value`. See [ARCHITECTURE.md → Token Format](ARCHITECTURE.md#token-format) for the full construction.

A row without an `id` produces a token derived from `canonical(value, type)`. Two un-grouped rows with different canonical values never collide (except by HMAC accident).

**Mixed literals and patterns** can share an `id` — they will all collapse to the same token:

```csv
id,value,type
acme,Acme Inc,org
acme,*-acme-*,org
acme,acme.com,org
```

**Caveat:** because the token depends on the `id` string, renaming `id` values invalidates a previously-written mapping. Treat `id` as stable. Full rationale and the operator stability matrix are in [HASHING.md → Why hash the `id` string](HASHING.md#4-why-hash-the-id-string-design-a) and [HASHING.md → Operator stability matrix](HASHING.md#7-operator-stability-matrix).

## Wildcard patterns

A `value` containing `*` or `?` is treated as a **pattern**, not a literal. Glob → regex translation is **type-aware** so wildcards do not bleed across delimiters:

| Type | `*` expands to | `?` expands to |
|---|---|---|
| `email` | `[^\s@,;<>]+` | one of the same class |
| `name`, `org`, `loc` | `[^\s,;]+` | one of the same class |
| `phone`, `iban`, `cc`, `ssn` | `\d+` | `\d` |
| (default) | `\S+` | `\S` |

Escape a literal `*` or `?` with a backslash: `\*`, `\?`.

### Token semantics for patterns

By default each unique match gets its **own** token:

```text
*@acme.com  →  alice@acme.com → <EMAIL:7f3a…>
            →  bob@acme.com   → <EMAIL:1c4d…>
```

If the row has an `id`, **all** matches collapse to one token:

```csv
id,value,type
acme,*@acme.com,email
```

```text
*@acme.com  →  alice@acme.com → <EMAIL:9b21…>
            →  bob@acme.com   → <EMAIL:9b21…>   # same id → same token
```

### Broad-pattern guard

Patterns that would match anything are rejected unless `--allow-broad-patterns` is set:

- `*`, `*@*`, `?`, `**`

This prevents silent over-substitution.

## Precedence

Literal beats pattern; longer match beats shorter; term list beats structured detector; structured beats NER. Full rules: [ARCHITECTURE.md → Span Precedence](ARCHITECTURE.md#span-precedence-overlap-resolution-in-replacerpy).

## Encoding & whitespace

- Files are read as UTF-8. Non-UTF-8 input → exit code `4`.
- Leading/trailing whitespace in `value` is stripped at load time.
- Empty `value` rows are skipped with a warning.

## Empty term lists

A file with only a header row, an empty file, or `/dev/null` is valid and yields zero literal/pattern detectors. Useful for structured-only or NER-only runs. Pass `--no-terms` to skip the `--terms` flag entirely.
