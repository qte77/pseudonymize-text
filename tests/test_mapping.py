from datetime import UTC, datetime
from pathlib import Path

from pseudonymize_text._schemas import MappingRecord
from pseudonymize_text.mapping import load_mapping, save_mapping


def test_mapping_round_trip(tmp_path: Path) -> None:
    now = datetime(2026, 5, 22, 14, 0, 0, tzinfo=UTC)
    mapping = {
        "<NAME:d273039bdb37a853c53f592bb1b460e0>": MappingRecord(
            value="John Doe",
            canonical="john doe",
            type="name",
            id="p1",
            first_seen=now,
            last_seen=now,
            occurrences=1,
        ),
    }
    mapping_path = tmp_path / "mapping.json"
    save_mapping(mapping_path, mapping)
    assert load_mapping(mapping_path) == mapping
