"""Standalone validator for a `terms.csv` / `terms.json` file.

Reuses the same ``load_terms`` helper that the literal/pattern detector
uses at runtime, so the lint and the detector cannot disagree on which
patterns are rejected. Exits non-zero on any load-time error (broad
pattern, unsupported extension, unparseable file).

Usage:
    uv run python -m pseudonymize_text.lint_terms tests/fixtures/terms.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

from .detectors.terms import load_terms


def main(argv: list[str] | None = None) -> int:
    """Return 0 on a clean term list, non-zero on any rejected pattern."""
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 1:
        print("usage: lint_terms <terms.csv|terms.json>", file=sys.stderr)
        return 2
    path = Path(args[0])
    try:
        load_terms(path)
    except (ValueError, OSError) as exc:
        print(f"lint_terms: {path}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI invocation
    raise SystemExit(main())
