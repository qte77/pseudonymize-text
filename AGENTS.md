# Agent Instructions for pseudonymize-text

Behavioral rules for AI coding agents working in this repository. The project is
a small utility library (≈5 modules) — keep ceremony proportional. Follow KISS,
DRY, and YAGNI; defer to the linked authoritative documents rather than restating
their rules here.

## Authoritative sources

Read in this order; do not duplicate their content into new files.

- [README.md](README.md) — what the tool does, quickstart, doc index.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — module layout, data flow, and the
  **Working norms** section: boundary failure-policy table + TDD per-behaviour discipline.
- [docs/HASHING.md](docs/HASHING.md) — token construction, canonicalization, stability matrix.
- [docs/SECURITY.md](docs/SECURITY.md) — threat model, key + mapping handling.
- [docs/COMPLIANCE.md](docs/COMPLIANCE.md) — GDPR / ENISA / EDPB / NIST posture.
- [docs/decisions/](docs/decisions/) — accepted architectural decisions ([MADR](https://adr.github.io/madr/) format, files `NNNN-title.md`). Cite by number (`ADR_NNN`) when a change implements or supersedes one; citations are independent of filename.

## Non-negotiable rules

- **Never re-tokenize output.** Tokens are terminal; do not feed `<TYPE:hex>`
  strings back through detection. Rationale in `docs/HASHING.md` §11.
- **Every I/O boundary has a row** in the boundary policy table
  (`docs/ARCHITECTURE.md` Working norms). A new `try/except` without a corresponding
  table row is incomplete — add the row in the same commit.
- **Red → Green per behaviour.** One failing test commit, one passing implementation
  commit, per observable behaviour. Regression-pin commits (Red only) are acceptable
  when a structural change in an earlier cycle already covers a behaviour.
- **Mapping file and HMAC key are never co-located with output.** Enforced by docs,
  not code — agents proposing changes that violate this must justify in the PR body.
- **Never read, log, or echo secret artefacts.** Files matching `.key` / `*.key`,
  the `PSEUDONYMIZE_KEY` env var, `pseudonymize-mapping.json`, and
  `pseudonymize-report.jsonl` are off-limits to agent context. Agent context windows
  are logged and persisted; ingesting these files is equivalent to exfiltrating
  them. Includes never writing secret values to anything under `~/.claude/`.

## Commands

Use `make` recipes; deviations need a reason.

- `make setup` — install runtime + dev + ner deps via uv
- `make test` — run pytest
- `make lint` — ruff check + markdownlint
- `make check` — lint + test (run before any commit)
- `make check_links` — lychee against README + docs/

## Escalation

Solo-maintainer project — no `AGENT_REQUESTS.md` by design (YAGNI). If a rule
above conflicts with a user instruction, ask the user; do not silently resolve.
