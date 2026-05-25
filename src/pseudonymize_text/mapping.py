"""JSON-backed mapping persistence (HASHING.md §10)."""

import json
import os
from pathlib import Path

from ._schemas import MappingRecord


def load_mapping(path: Path) -> dict[str, MappingRecord]:
    """Load mapping from ``path``; return empty dict if the file does not exist."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {token: MappingRecord.model_validate(rec) for token, rec in raw.items()}


def save_mapping(path: Path, mapping: dict[str, MappingRecord]) -> None:
    """Persist ``mapping`` atomically to ``path`` via tmp file plus ``os.replace``.

    Tmp file is created with mode ``0o600`` so plaintext mapping bytes are not
    world-readable during the write window (umask-independent).
    """
    serialized = {token: rec.model_dump(mode="json") for token, rec in mapping.items()}
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(serialized, indent=2))
    os.replace(tmp, path)


def upsert(
    mapping: dict[str, MappingRecord], token: str, incoming: MappingRecord
) -> None:
    """Insert or merge ``incoming`` per HASHING.md §10 append-with-update semantics."""
    existing = mapping.get(token)
    if existing is None:
        mapping[token] = incoming
        return
    mapping[token] = existing.model_copy(
        update={
            "last_seen": incoming.last_seen,
            "occurrences": existing.occurrences + incoming.occurrences,
        }
    )
