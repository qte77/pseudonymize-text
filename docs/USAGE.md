# Usage

*For operators running the CLI.*

## Subcommands

```text
pseudonymize detect <in_dir>          [opts]   # report only; no writes to in/ or out/
pseudonymize apply  <in_dir> <out_dir> [opts]  # detect (or load --plan) and write
```

There is no implicit one-shot — `apply` is always the writing command. Use `detect` first when working with new data or new term lists.

## Required Inputs

| Input | How provided |
|---|---|
| Secret key | `PSEUDONYMIZE_KEY` env var **or** `--key-file PATH` (CLI flag wins if both present) |
| Term list | `--terms FILE` (CSV or JSON; see [TERMS_CSV.md](TERMS_CSV.md)) |

If neither key source is set, exit code `3`. If `--terms` cannot be read or parsed, exit code `4`.

## Flags

### Common to `detect` and `apply`

| Flag | Default | Purpose |
|---|---|---|
| `--terms FILE` | (required unless `--no-terms`) | Term list (CSV or JSON). Empty file allowed. |
| `--no-terms` | off | Run without a term list (structured/NER only). Mutually exclusive with `--terms`. |
| `--detectors LIST` | `literal,structured` | Comma list from `literal`, `structured`, `ner`. |
| `--types LIST` | `name,email,phone,iban,cc,ssn,org,loc` | **Filter** on entity types — does not enable detectors. Types not produced by enabled detectors are simply unused. |
| `--key-file PATH` | — | Read HMAC key from this file (overrides env var). |
| `--report PATH` | `./pseudonymize-report.jsonl` | Where to write the audit report. Must **not** reside inside `<out_dir>`; exit `7` otherwise (same rule as `--mapping`, since the report holds plaintext spans). |
| `--report-format FMT` | `jsonl` | `jsonl` or `tsv`. |
| `--ignore FILE` | — | Suppression list (one literal per line, `#` comments). Matches a span's surface `text` field; comparison is NFKC + casefold. |
| `--allow-broad-patterns` | off | Permit term-list patterns that match `*`/`*@*`/`?`. |
| `--ner` | off | Enable NER detector (requires `[ner]` extra). |
| `--ner-model NAME` | `xx_ent_wiki_sm` | spaCy model name. |
| `--ner-confidence FLOAT` | `0.85` | Drop NER spans below this score. |
| `--ner-extensions LIST` | `.txt,.md,.log` | File extensions where NER runs. |
| `--ner-stoplist FILE` | — | Words NER must never tag (one per line). |
| `--ner-max-bytes N` | `5242880` (5 MB) | Skip NER on files larger than this; literals/structured still run. |
| `-v`, `--verbose` | off | Per-file progress. |
| `--quiet` | off | Suppress non-error output. |

### `apply` only

| Flag | Default | Purpose |
|---|---|---|
| `--plan FILE` | — | Re-use the spans from a prior `detect` JSONL report instead of re-detecting. When given, `--terms` becomes optional and is ignored; `--detectors` and `--types` are read from the plan header. The HMAC key is still required (tokens are recomputed from the key, so the plan is portable across keys). |
| `--mapping PATH` | `./pseudonymize-mapping.json` | Where to write the token → plaintext map (must be **outside** `<out_dir>` — see [SECURITY.md](SECURITY.md)). |
| `--overwrite` | off | Allow `--mapping` and `<out_dir>` to overwrite existing files. |

`apply` always emits a report (echoing the plan when `--plan` is given). See [ARCHITECTURE.md → Report Schema](ARCHITECTURE.md#report-schema-jsonl).

## Environment Variables

| Var | Purpose |
|---|---|
| `PSEUDONYMIZE_KEY` | Hex-encoded HMAC secret. Used if `--key-file` is not given. |

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `2` | Usage error (bad flag, missing argument). |
| `3` | Missing or invalid HMAC key. |
| `4` | Missing or unparseable `--terms`, `--ignore`, or `--plan`. |
| `5` | Detector initialization error (e.g. spaCy model not installed). |
| `6` | I/O error during walk or write. |
| `7` | `apply --plan` aborted: mapping path is inside `<out_dir>` or path-safety check failed. |

## Workflow

```bash
# Generate key (one-time)
openssl rand -hex 32 > .key
chmod 600 .key

# 1. Detect — audit the plan
PSEUDONYMIZE_KEY=$(cat .key) \
  pseudonymize detect ./corpus \
    --terms terms.csv \
    --report plan.jsonl

# 2. Review plan.jsonl; build an --ignore list of false positives if needed
jq -r 'select(.detector | startswith("ner")) | "\(.text)\t\(.confidence)\t\(.file)"' plan.jsonl

# 3. Apply — byte-identical to the audited plan
PSEUDONYMIZE_KEY=$(cat .key) \
  pseudonymize apply ./corpus ./out \
    --terms terms.csv \
    --plan plan.jsonl \
    --ignore false-positives.txt \
    --mapping ./pseudonymize-mapping.json
```

After `apply`, three artifacts exist:

- `./out/` — mirrored corpus with tokens (safe to share).
- `./pseudonymize-mapping.json` — token ↔ plaintext map (treat as **secret**).
- `./pseudonymize-report.jsonl` — audit trail of what was substituted (treat as secret if it contains plaintext).

## Examples

**Discovery pass** (NER only, no writes; surface unknown entities to add to `terms.csv`):

```bash
pseudonymize detect ./corpus \
  --terms terms.csv \
  --detectors ner \
  --ner --ner-confidence 0.9 \
  --report discovery.jsonl
```

**Structured-only pass** (find all IBANs/SSNs irrespective of term list):

```bash
pseudonymize detect ./corpus --no-terms \
  --detectors structured \
  --types iban,cc,ssn \
  --report structured.jsonl
```

**Single trusted-corpus run** (skip explicit `detect`):

```bash
pseudonymize apply ./corpus ./out --terms terms.csv
```

A report is still written — `apply` never runs blind.

**Mail corpus** (`.eml` / `.mbox`):

`.eml` and `.mbox` extensions are auto-routed through `formats/` per [ADR_002](decisions/ADR_002.md) — no extra flag. Headers (incl. RFC 2047 encoded), `text/plain`, and `text/html` parts are pseudonymized; non-text parts are replaced with a `[part removed by pseudonymize: <ctype>; <N> bytes]` stub; `DKIM-Signature` and `ARC-*` headers are stripped (signatures are invalid after rewrite); `.mbox` inputs fan out to per-message `.eml` files at `<out_dir>/<basename>/<seq>.eml` — no mbox re-assembly.

```bash
pseudonymize detect ./mail-in --terms terms.csv --ner --report plan.jsonl
# review plan.jsonl (especially NER spans), build false-positives.txt
pseudonymize apply ./mail-in ./mail-out \
  --terms terms.csv --plan plan.jsonl --ignore false-positives.txt
```

For unsupported PHI categories in clinical mail, see [landscape/de-identification.md](landscape/de-identification.md). The part-fate table lives in [ARCHITECTURE.md § Mail-format support](ARCHITECTURE.md#mail-format-support).
