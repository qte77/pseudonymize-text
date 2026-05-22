"""JSON-backed mapping persistence (HASHING.md §10)."""

import json
from pathlib import Path

from ._schemas import MappingRecord


def load_mapping(path: Path) -> dict[str, MappingRecord]:
    """Load mapping from ``path``; return empty dict if the file does not exist."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {token: MappingRecord.model_validate(rec) for token, rec in raw.items()}


def save_mapping(path: Path, mapping: dict[str, MappingRecord]) -> None:
    """Persist ``mapping`` to ``path`` as a JSON object keyed by token."""
    serialized = {token: rec.model_dump(mode="json") for token, rec in mapping.items()}
    path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")
