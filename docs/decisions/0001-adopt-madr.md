---
status: accepted
date: 2026-05-25
---

# Adopt MADR for architectural decisions

## Context and Problem Statement

The project will accumulate non-obvious design decisions (mail-part handling,
detector precedence, key-rotation procedure). Recording rationale inline in
[ARCHITECTURE.md](../ARCHITECTURE.md) mixes "what is" with "why we chose it";
both decay together. A separate, append-only log is needed.

## Decision Drivers

* Decisions must survive author hand-off — rationale, not just outcome.
* Solo-maintainer project — ceremony must be low.
* [ARCHITECTURE.md](../ARCHITECTURE.md) stays a current-state reference, not a
  changelog.

## Considered Options

* [MADR 4](https://adr.github.io/madr/) (Markdown Architectural Decision Records).
* Free-form notes appended to [ARCHITECTURE.md](../ARCHITECTURE.md).
* GitHub Discussions / Issues only.

## Decision Outcome

Chosen: **MADR 4** with canonical layout.

* Location: `docs/decisions/` (per MADR canonical layout; renamed from `docs/ADR/` 2026-05-26).
* Filename: `NNNN-title.md` (per MADR canonical layout; renamed from `ADR_###.md` 2026-05-26).
* Frontmatter: only `status` and `date`; Jekyll-specific fields omitted.
* Citation: by decision number (`ADR_NNN`) in source/tests/CHANGELOG, independent of filename. Filename may change if a title is refined; citations do not.

### Consequences

* Good — decisions are referenceable from issues, PRs, and
  [ARCHITECTURE.md](../ARCHITECTURE.md).
* Good — append-only; no merge conflicts on "what changed".
* Good — filenames carry the title (per canonical MADR), so the decision subject is visible in directory listings.
