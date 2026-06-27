### Fixed

- Mail (`.eml`/`.mbox`) output is now deterministic. Pseudonymized headers are replaced in place instead of being deleted and re-added, which had re-ordered them in per-process (hash-randomized) `frozenset` order — so the same input + key now produces byte-identical output across runs, restoring the determinism guarantee for mail.
