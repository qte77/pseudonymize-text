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
| `--report PATH` | `./runs/pseudonymize-report.jsonl` | Where to write the audit report. Parent directory is auto-created. Must **not** reside inside `<out_dir>`; exit `7` otherwise (same rule as `--mapping`, since the report holds plaintext spans). |
| `--report-format FMT` | `jsonl` | `jsonl` or `tsv`. |
| `--ignore FILE` | — | Suppression list (one literal per line, `#` comments). Matches a span's surface `text` field; comparison is NFKC + casefold. |
| `--ner` | off | Enable NER detector (requires `[ner]` extra). |
| `--allow-broad-patterns` | off | Allow broad term patterns (`*`, `?`, `*@*`, `**`) that the loader rejects by default (exit `4`). |

### `apply` only

| Flag | Default | Purpose |
|---|---|---|
| `--plan FILE` | — | Re-use the spans from a prior `detect` JSONL report instead of re-detecting. When given, `--terms` becomes optional and is ignored; `--detectors` and `--types` are read from the plan header. The HMAC key is still required (tokens are recomputed from the key, so the plan is portable across keys). |
| `--mapping PATH` | `./runs/pseudonymize-mapping.json` | Where to write the token → plaintext map. Parent directory is auto-created. Must be **outside** `<out_dir>` — see [SECURITY.md](SECURITY.md). |

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
| `7` | `apply` aborted by path-safety check: `--mapping` or `--report` resolves inside `<out_dir>`, or `--plan` `config_hash` does not match the current key fingerprint. |

## Workflow

```bash
# Generate key (one-time)
openssl rand -hex 32 > .key
chmod 600 .key

# Stage every artefact under runs/ — the directory is gitignored
mkdir -p runs

# 1. Detect — audit the plan
PSEUDONYMIZE_KEY=$(cat .key) \
  pseudonymize detect runs/in \
    --terms runs/terms.csv \
    --report runs/plan.jsonl

# 2. Review plan.jsonl; build an --ignore list of false positives if needed
jq -r 'select(.detector | startswith("ner")) | "\(.text)\t\(.confidence)\t\(.file)"' runs/plan.jsonl

# 3. Apply — byte-identical to the audited plan
PSEUDONYMIZE_KEY=$(cat .key) \
  pseudonymize apply runs/in runs/out \
    --terms runs/terms.csv \
    --plan runs/plan.jsonl \
    --ignore runs/false-positives.txt \
    --mapping runs/mapping.json \
    --report runs/report.jsonl
```

After `apply`, three artifacts exist:

- `runs/out/` — mirrored corpus with tokens (safe to share).
- `runs/mapping.json` — token ↔ plaintext map (treat as **secret**).
- `runs/report.jsonl` — audit trail of what was substituted (treat as secret if it contains plaintext).

## Examples

**Discovery pass** (NER only, no writes; surface unknown entities to add to `terms.csv`):

```bash
pseudonymize detect runs/in \
  --terms runs/terms.csv \
  --detectors ner \
  --ner \
  --report runs/discovery.jsonl
```

**Structured-only pass** (find all IBANs/SSNs irrespective of term list):

```bash
pseudonymize detect runs/in --no-terms \
  --detectors structured \
  --types iban,cc,ssn \
  --report runs/structured.jsonl
```

**Single trusted-corpus run** (skip explicit `detect`):

```bash
pseudonymize apply runs/in runs/out --terms runs/terms.csv
```

A report is still written — `apply` never runs blind.

**Mail corpus** (`.eml` / `.mbox`):

`.eml` and `.mbox` extensions are auto-routed through `formats/` per [ADR_002](decisions/ADR_002.md) — no extra flag. Headers (incl. RFC 2047 encoded), `text/plain`, and `text/html` parts are pseudonymized; non-text parts are replaced with a `[part removed by pseudonymize: <ctype>; <N> bytes]` stub; `DKIM-Signature` and `ARC-*` headers are stripped (signatures are invalid after rewrite); `.mbox` inputs fan out to per-message `.eml` files at `<out_dir>/<basename>/<seq>.eml` — no mbox re-assembly.

```bash
pseudonymize detect runs/mail-in --terms runs/terms.csv --ner --report runs/plan.jsonl
# review runs/plan.jsonl (especially NER spans), build runs/false-positives.txt
pseudonymize apply runs/mail-in runs/mail-out \
  --terms runs/terms.csv --plan runs/plan.jsonl --ignore runs/false-positives.txt
```

Mail parts are **re-detected at `apply` time even under `--plan`** — the plan keys spans by file, which cannot be replayed across a message's MIME parts — so keep `--terms` on the `apply` command for mail corpora (text files still replay from the plan). Detection is deterministic, so the result matches the audited plan. Tokens placed in address headers (`From` / `To` / …) are emitted RFC 2047-encoded and decode back to `<TYPE:hex>`.

For unsupported PHI categories in clinical mail, see [landscape/de-identification.md](landscape/de-identification.md). The part-fate table lives in [ARCHITECTURE.md § Mail-format support](ARCHITECTURE.md#mail-format-support).
