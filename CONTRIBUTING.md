<!--
  CONTRIBUTING for pseudonymize-text, per the qte77 estate contract:
  https://github.com/qte77/qte77/blob/main/docs/doc-structure.md
-->

# Contributing

For agent behavioural rules and the decision framework see [AGENTS.md](AGENTS.md);
for design rationale and the boundary/TDD working norms see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). This file owns the contributor
workflow — commands, conventions, and releasing — and does not restate those.

## Documentation hierarchy

One audience per file — reference, don't duplicate (estate contract:
[doc-structure.md](https://github.com/qte77/qte77/blob/main/docs/doc-structure.md)):

| File | Audience | Owns |
| --- | --- | --- |
| [README.md](README.md) | users / evaluators | what this is, why, how — the front door |
| CONTRIBUTING.md (this file) | contributors | workflow, commands, conventions, releasing |
| [AGENTS.md](AGENTS.md) | AI agents | behavioural rules, decision framework (`CLAUDE.md` loads the same) |
| [CHANGELOG.md](CHANGELOG.md) | everyone | notable changes by version (Keep a Changelog) |

## Commands

Use `make` recipes; deviations need a reason.

```bash
make setup           # install runtime + dev + ner deps via uv
make test            # pytest (coverage gate >= 80%)
make lint            # ruff check + markdownlint
make format          # ruff format
make check           # lint + test (run before any commit)
make check_links     # lychee against README + docs/
make lint_terms      # validate a terms.csv for ReDoS / broad patterns
make changelog_new   # add a changelog fragment under changelog.d/
```

## Conventional Commits

`feat`, `fix`, `docs`, `chore`, `refactor`, `test`. Optional scope: `feat(SCOPE): …`. PR titles match.

## Branches

- `feat/TOPIC`, `fix/TOPIC`, `docs/TOPIC`, `chore/TOPIC` — branch off `main`; never commit to `main` directly.
- Squash-merge is default. Force-push only with `--force-with-lease`, never to `main`.
- In this dev container, prefix `git`/`gh` with `env -u GH_TOKEN -u GITHUB_TOKEN` when a stale token shadows your `gh auth` credentials.

## CHANGELOG

Add a `changelog.d/` fragment for any consumer-visible change: `make changelog_new` creates
one; fill the category (`Added` / `Changed` / `Fixed` / …) and a bullet ending with the
issue/PR ref. `make changelog_preview` shows the assembled entry. Fragments are collected into
`CHANGELOG.md` at release time (below).

## Releasing

SemVer; the version source of truth is `pyproject.toml` `[project].version` (mirrored in
`src/pseudonymize_text/__init__.py` and the README version badge). `CHANGELOG.md` is assembled
by [scriv](https://scriv.readthedocs.io) from `changelog.d/` fragments.

1. **Bump** (maintainer): run **bump-my-version** (`patch` / `minor` / `major`) from the Actions
   tab. It bumps `pyproject.toml` + `src/pseudonymize_text/__init__.py` + the README badge,
   **syncs `uv.lock`**, collects fragments into `CHANGELOG.md`, and opens a `chore(release): bump …` PR.
2. **Run the PR's checks.** It's bot-authored, so its checks idle at `action_required` until a
   real-user event — push any commit to the bump branch, or close + reopen the PR.
3. **Merge on green**: `gh pr merge <n> --squash --admin --delete-branch`. **tag-release** then
   fires on `main` and tags the merge commit `vX.Y.Z` (always reachable from `main`).
4. Optionally run **publish-release** for a GitHub Release with notes from the `CHANGELOG.md`
   block. Tag-only is the default.

## Pre-merge

1. `make check` green (ruff + markdownlint + pytest ≥ 80%)
2. `make check_links` clean
3. `changelog.d/` fragment added for consumer-visible changes
4. Conventional Commits PR title
