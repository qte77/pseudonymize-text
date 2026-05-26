# Architecture

*For implementers and reviewers wiring the modules together.*

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
src/pseudonymize_text/
  cli.py            # argparse entry; detect / apply subcommands
  walker.py         # mirror in/ → out/, extension whitelist
  formats/          # .eml / .mbox readers and writers (see ADR_002)
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

`<TYPE:hexdigits>` where `TYPE` ∈ {`NAME`, `EMAIL`, `PHONE`, `IBAN`, `CC`, `SSN`, `ORG`, `LOC`} and `hexdigits` is 32 lowercase hex characters (128-bit truncated HMAC-SHA256).

Construction, canonicalization, kind-namespacing, and design rationale: [HASHING.md](HASHING.md). Key handling: [SECURITY.md](SECURITY.md). Regulatory mapping: [COMPLIANCE.md](COMPLIANCE.md).

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
  "text": "John Doe",
  "detector": "literal",
  "type": "name",
  "id": "p1",
  "token": "<NAME:7f3a9c8b…>",
  "context": "…signed in: John Doe from…"
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
| Symlinks (files) | Resolved; resolved path must remain under `<in_dir>` (else exit `6`). Target read once. |
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

- **New entity type** → add a detector in `src/pseudonymize_text/detectors/`, register its enum value, expose in `--detectors`.
- **New file type** (PDF, docx — deferred) → add a reader/writer to `walker.py`; pipeline downstream is unchanged.
- **Embedded use** → import `pseudonymize_text.transform(text, config) -> (text, mapping_delta)` (public API, deferred to 1.0.0; see [roadmap](roadmap.md)).

## Default File Extensions

`.txt .md .log .py .json .yaml .yml .csv .toml .ini` — read/write as UTF-8. `.eml` and `.mbox` are routed through the formats layer (see [Mail-format support](#mail-format-support) below). Anything else is copied through unchanged. PDF and Office formats are deferred.

## Mail-format support

`.eml` and `.mbox` inputs are handled by `formats/` rather than the default UTF-8 read path. Per [ADR_002](ADR/ADR_002.md):

| Part | Fate |
|---|---|
| Headers (`From`, `To`, `Cc`, `Bcc`, `Subject`, `Reply-To`, incl. RFC 2047 encoded) | Decoded, pseudonymized, re-encoded. |
| `text/plain` parts | Decoded (transfer encoding + charset), pseudonymized, re-encoded. |
| `text/html` parts | Same as `text/plain`. Detector strategy is settled in `detectors/structured.py` ([#11](https://github.com/qte77/pseudonymize-text/issues/11)). |
| Other MIME parts (binary attachments, inline images, S/MIME, `application/*`) | **Dropped.** Replaced by a `text/plain` stub: `[part removed by pseudonymize: <Content-Type>; <N> bytes]`. |
| `DKIM-Signature`, `ARC-*` headers | Stripped (signatures are invalid after step 1). |

`.mbox` inputs fan out to per-message `.eml` files at `<out_dir>/<basename>/<seq>.eml`; no mbox re-assembly. Rationale and full consequences: [ADR_002](ADR/ADR_002.md).

## What's deferred

See [roadmap.md](roadmap.md) for milestones (0.2.0, 1.0.0, 2.0.0).

## Working norms

Conventions every contribution follows.

### Boundary failure-policy

Every I/O boundary is pinned to **one** policy. Reviewers consult this table when a new `try/except` shows up; if a boundary isn't listed, the row is the first thing to add.

| Policy | Meaning |
|---|---|
| `fail-loud` | Raise immediately. Failure is a programmer / infra / config problem that silent degradation would hide. |
| `wrap-degrade` | Catch a specific exception, log `WARNING`, return a degraded result (`None`, sparse, empty). |
| `wrap-continue` | `wrap-degrade` inside a loop; per-item failure doesn't abort the batch. |

| Boundary | Where | Policy |
|---|---|---|
| HMAC over canonical subject | `tokenize.hmac_token` | `fail-loud` (programmer error if `kind` or `type_` is bad). The raw `key` parameter and the derived `mac_key` are scrubbed from frame locals (via `del` + `try/finally`) so neither survives in a traceback if the HMAC computation raises. |
| Per-type canonicalization | `tokenize.canonicalize` | `fail-loud` (`ValueError` on unknown type; `phonenumbers.NumberParseException` propagated). |
| Mapping JSON load | `mapping.load_mapping` | `fail-loud` (corrupt JSON or `ValidationError` on missing/extra fields). |
| Mapping JSON save | `mapping.save_mapping` | `fail-loud` (disk full / permission denied propagated mid-rename; tmp file may be left behind, next save overwrites it). Tmp file is created with mode `0o600` (umask-independent) so plaintext bytes are not world-readable during the write window. |
| Report JSONL append | `report.ReportWriter.write` | `fail-loud` (disk full / permission denied). |
| Plan-file containment | `cli` plan loader | `fail-loud` (exit 4 if any `ReportRecord.file` contains `..`, is absolute, or resolves outside `<out_dir>`; prevents an operator-supplied plan from mirroring to arbitrary filesystem locations). |
| Walker file enumeration | `walker.walk_and_process` | `fail-loud` (raises `SymlinkEscapeError` when a file symlink in `<in_dir>` resolves outside; UTF-8 decode errors propagate from `Path.read_text`; disk failures propagate from the atomic-write helper). Tmp output files are opened with mode `0o600` (umask-independent). |
| Term-list load | `detectors.terms.load_terms` | `fail-loud` (raises `ValueError` on unsupported extension, broad pattern `*`/`*@*`/`?`/`**` without `allow_broad`, or malformed CSV/JSON; the same helper backs `lint_terms` so detector and lint cannot disagree). |
| Structured-detector validation | `detectors.structured.detect_*` | `wrap-continue`. `python-stdnum`'s `iban.is_valid` / `luhn.is_valid` are predicates (do not raise); `phonenumbers.PhoneNumberMatcher` swallows its own parse errors and yields only valid candidates. Lookalikes that fail validation are silently skipped so a single false-positive does not abort the file. |
| NER detector lazy import | `detectors.ner.detect_ner` | `fail-loud` (raises `ImportError` with `[ner]`-extra install hint if `spacy` is not installed). spaCy's own model load (`spacy.load(model_name)`) propagates `OSError` if the model is not installed. See [docs/ner-install.md](ner-install.md) for the hash-pinned installation procedure. |

### TDD per-behaviour discipline

One **Red** commit (failing test) → one **Green** commit (passing impl) per observable behaviour. Commits stay tiny; CI runs against each.

For behaviours that pass by design (a structural change in cycle N already covers cycle N+M): commit the Red test anyway as a **regression-pin commit** — no separate Green.
