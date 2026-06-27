# Examples

A ready-to-run, end-to-end demo of `pseudonymize-text` over a small bundled corpus.

## Run it

From the repo root:

```bash
make demo
```

It generates an **ephemeral** HMAC key, runs `detect` then `apply --plan` over
[`in/`](in/) using [`terms.csv`](terms.csv), and writes the pseudonymized result
to `examples/_out/out/` (gitignored). The key is not retained, so each run
produces fresh tokens — and no key, mapping, or plaintext is ever committed.

`make demo` enables every detector group
(`--detectors literal,structured,phi,eu --phi-context`) so the full range fires:
names / orgs / locations (literal terms), email / phone / IBAN / card / SSN
(structured), NPI / DEA / VIN / MRN (US PHI), and the EU national IDs
(DE / FR / GB / ES / IT).

## What's in `in/`

| File | Source / licence | Exercises |
|---|---|---|
| `rfc2822-excerpt.txt` | RFC 2822 example messages (IETF; freely distributable) | structured email detection (zero-config) + literal names |
| `lincoln-letter-excerpt.txt` | Lincoln letter, 1848 (Project Gutenberg; public domain) | literal name / location via `terms.csv` |
| `dummy-record.md` | **synthetic — every value fabricated** (IDs are checksum-valid so validators fire) | the full detector matrix incl. opt-in PHI + EU IDs |

## Larger / real-world corpus

`pseudonymize-text` is **text-only** — it pseudonymizes `.txt` / `.md` / `.eml`
and byte-copies or skips binaries. For a bigger, real-world test set, the sibling
[**doc-pipeline-engine**](https://github.com/qte77/doc-pipeline-engine) ships a
`samples/` corpus: its `.txt` files (Gutenberg letters, RFCs) are directly
consumable here; its PDF / DOCX samples become consumable once run through
doc-pipeline-engine's text extraction first.
