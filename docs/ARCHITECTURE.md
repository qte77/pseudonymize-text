# Architecture

## Stack

| Layer | Choice | Reference |
|---|---|---|
| Language | Python ≥ 3.11 | <https://docs.python.org/3/> |
| Detection — structured IDs | `python-stdnum` (IBAN mod-97, CC Luhn) | <https://arthurdejong.org/python-stdnum/> |
| Detection — phone | `phonenumberslite` (port of Google libphonenumber) | <https://pypi.org/project/phonenumberslite/> · <https://github.com/google/libphonenumber> |
| Detection — NER (optional) | spaCy + `xx_ent_wiki_sm` (~12 MB, multilingual) | <https://spacy.io/models> |
| Tokenization | stdlib `hmac` + `hashlib` (SHA-256) | <https://docs.python.org/3/library/hmac.html> · <https://www.rfc-editor.org/rfc/rfc2104> · <https://csrc.nist.gov/pubs/fips/180-4/upd1/final> |
| Packaging | `pyproject.toml` (PEP 517/518) | <https://packaging.python.org/en/latest/specifications/pyproject-toml/> |
| Tests | `pytest` | <https://docs.pytest.org/> |

## Module Layout

```text
src/pseudonymize/
  cli.py            # argparse entry; detect / apply subcommands
  walker.py         # mirror in/ → out/, extension whitelist
  detectors/
    terms.py        # literals + id-grouping + wildcards (CSV/JSON loader)
    structured.py   # email, phone, iban, cc, ssn
    ner.py          # spaCy adapter (optional import)
  replacer.py       # span dedupe + right-to-left substitution
  tokenize.py       # HMAC-SHA256, key loading, type namespacing
  mapping.py        # token <-> plaintext store (JSON)
  report.py         # JSONL/TSV writers, summary
tests/
pyproject.toml      # core deps + [ner] optional extra
Makefile            # setup / run / test / lint
```

## Data Flow

```text
┌────────────────────────────────────────────────────────────────────┐
│  CLI (cli.py)                                                      │
│    detect <in>           --terms --detectors --ner --report …      │
│    apply  <in> <out>     --terms --plan --ignore --key-file …      │
└──────────────┬─────────────────────────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────────────────────────┐
│  walker.py — mirror in/ → out/                                     │
│    extensions: .txt .md .log .py .json .yaml .yml .csv .toml .ini  │
└──────────────┬─────────────────────────────────────────────────────┘
               │ text per file
               ▼
┌────────────────────────────────────────────────────────────────────┐
│  detectors/  → list of Span(start, end, text, type, source, conf?) │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────────┐  │
│  │ terms.py        │ │ structured.py   │ │ ner.py (optional)    │  │
│  │  literal + \b   │ │  email   re     │ │  spaCy multilingual  │  │
│  │  id grouping    │ │  phone   libph  │ │  PERSON / ORG / LOC  │  │
│  │  wildcards      │ │  iban    stdnum │ │  prose ext only      │  │
│  │                 │ │  cc Luhn stdnum │ │                      │  │
│  │                 │ │  ssn     re     │ │                      │  │
│  └─────────────────┘ └─────────────────┘ └──────────────────────┘  │
└──────────────┬─────────────────────────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────────────────────────┐
│  replacer.py                                                       │
│   1. dedupe overlaps   (literal > structured > NER, longest wins)  │
│   2. apply --ignore    (suppression list)                          │
│   3. right-to-left single-pass substitution (no offset drift)      │
└──────────┬─────────────────────────────────────┬───────────────────┘
           │ token request                       │ apply mode only
           ▼                                     ▼
┌──────────────────────────┐    ┌───────────────────────────────────┐
│  tokenize.py             │    │  report.py                        │
│   key = env | --key-file │    │   JSONL / TSV writer              │
│   token(subject, type) = │    │   per-type counts, files affected │
│     "<" + TYPE + ":" +   │    │   produced by `detect`            │
│     hmac_sha256(         │    │   re-emitted by `apply`           │
│       key||":"||type,    │    └───────────────────────────────────┘
│       kind||":"||subject │
│     )[:16].hex() + ">"   │
│   kind ∈ {"id","v"};     │
│   subject = group id     │
│     or canonical(value)  │
└──────────┬───────────────┘
           ▼
┌────────────────────────────────────────────────────────────────────┐
│  mapping.py — pseudonymize-mapping.json (next to, not inside, out/)│
│    JSON: { token → record }                                        │
│    See HASHING.md §10 for the normative schema (value, canonical,  │
│    type, id, first_seen, last_seen, occurrences).                  │
└────────────────────────────────────────────────────────────────────┘
```

## Stages

| Stage | Walks files? | Runs detectors? | Writes `out/` | Writes mapping | Writes report |
|---|---|---|---|---|---|
| `detect` | yes | yes | no | no | yes |
| `apply` (no `--plan`) | yes | yes | yes | yes | yes |
| `apply --plan FILE` | yes | no (plan reused) | yes | yes | yes (echoed plan) |

Re-using the plan in `apply --plan` guarantees byte-identical output to what was audited, even if NER models or term lists drift.

## Token Format

```text
<TYPE:hexdigits>
```

- `TYPE` ∈ uppercase enum: `NAME`, `EMAIL`, `PHONE`, `IBAN`, `CC`, `SSN`, `ORG`, `LOC`.
- `hexdigits` = 32 lowercase hex characters = 128 bits.
- Construction:

  ```text
  hexdigits = HMAC-SHA256(key || ":" || type, kind || ":" || subject)[:16].hex()
  ```

  | Source of span | `kind` | `subject` |
  |---|---|---|
  | Term-list row with `id` (literal or pattern) | `"id"` | the row's `id` string |
  | Term-list row without `id` | `"v"` | `canonical(value, type)` (see below) |
  | Pattern match without `id` | `"v"` | `canonical(matched_text, type)` |
  | Structured detector (email/phone/iban/cc/ssn) | `"v"` | `canonical(matched_text, type)` |
  | NER hit | `"v"` | `canonical(matched_text, type)` |

  `kind` namespacing prevents construction of a value that would collide with an `id`-derived token.

- 128-bit truncation per [NIST SP 800-107r1 §5.1](https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-107r1.pdf).

Full rationale (canonicalization rules per type, `kind` namespacing, Design A vs alternatives, stability matrix, dependency-stability commitment, mapping schema) lives in [HASHING.md](HASHING.md). See [SECURITY.md](SECURITY.md) for key handling and [COMPLIANCE.md](COMPLIANCE.md) for the regulatory rationale.

## Report Schema (JSONL)

One JSON object per line. Read by `apply --plan`; written by both `detect` and `apply`.

```json
{
  "schema": "pseudonymize.report/1",
  "file": "logs/app.log",
  "line": 42,
  "col": 17,
  "start": 1083,
  "end": 1097,
  "text": "Alice Müller",
  "detector": "literal",
  "type": "name",
  "id": "p1",
  "token": "<NAME:7f3a9c8b…>",
  "context": "…signed in: Alice Müller from…"
}
```

| Field | Type | Notes |
|---|---|---|
| `schema` | string | Version tag; consumers reject unknown majors. Emitted on the first record of a run only. |
| `file` | string | Path relative to `<in_dir>`. POSIX separators. |
| `line` | int | 1-based, line of `start`. |
| `col` | int | 1-based, column of `start`. |
| `start`, `end` | int | **Character** offsets (UTF-8 source decoded to `str`); `end` is exclusive. |
| `text` | string | Surface form actually matched. |
| `detector` | string | `"literal"`, `"pattern"`, `"structured:<name>"` (e.g. `"structured:email"`), `"ner:<label>"` (e.g. `"ner:PERSON"`). |
| `type` | string | Lowercase entity type. |
| `id` | string \| null | Group `id` from term row, or `null`. |
| `token` | string | Token to substitute. Recomputed from key at `apply` time when running with `--plan`; the value in the plan is informational. |
| `confidence` | float \| null | NER spans only. |
| `context` | string | ±40 chars around the span; truncated at line boundaries. |

The first line of a report is a header object: `{"schema": "...", "tool_version": "...", "started_at": "...", "config_hash": "..."}`. `apply --plan` aborts with exit `7` if the plan's `config_hash` (over enabled detectors, types, and key fingerprint) does not match the current invocation.

## Walker behavior

| Aspect | Behavior |
|---|---|
| Symlinks (dirs) | Not followed by default. |
| Symlinks (files) | Resolved and processed (target read once). |
| Hidden files (`.*`) | Processed. |
| Whitelisted extensions | Read as UTF-8, processed, written to mirrored path. |
| Other extensions | Copied byte-for-byte to mirrored path. |
| `<in_dir>` symlinks pointing outside the input root | Refused; exit `6`. |

## Span Precedence (overlap resolution in `replacer.py`)

When two detectors emit overlapping spans:

1. **Source rank**: literal > structured > NER.
2. **Length tiebreak**: longer span wins.
3. **Suppression**: spans matching `--ignore` are dropped after dedup.

This guarantees a curated `terms.csv` entry always overrides a structured or NER guess for the same string.

## Extension Points

- **New entity type** → add a detector in `src/pseudonymize/detectors/`, register its enum value, expose in `--detectors`.
- **New file type** (PDF, docx — deferred) → add a reader/writer to `walker.py`; pipeline downstream is unchanged.
- **Embedded use** → import `pseudonymize.replacer.transform(text, config) -> (text, mapping_delta)` (public API, deferred to v1.1).

## Default File Extensions

`.txt .md .log .py .json .yaml .yml .csv .toml .ini` — read/write as UTF-8. Anything else is copied through unchanged. PDF and Office formats are deferred.

## What's deferred

PDF / Office, `--expand-names` auto-variants, reverse mode, streaming, parallel files, SQLite mapping backend, encrypted mapping, key-rotation tool, SARIF, GLiNER/HF NER backends, public Python API.
