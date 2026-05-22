from datetime import UTC, datetime
from pathlib import Path

import pytest

from pseudonymize_text._schemas import MappingRecord
from pseudonymize_text.mapping import load_mapping, save_mapping, upsert


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


def test_upsert_existing_token_preserves_first_seen_and_sums_occurrences() -> None:
    t1 = datetime(2026, 5, 22, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 5, 22, 14, 0, 0, tzinfo=UTC)
    key = "<NAME:d273039bdb37a853c53f592bb1b460e0>"
    fields = {"value": "John Doe", "canonical": "john doe", "type": "name", "id": "p1"}
    mapping = {
        key: MappingRecord(**fields, first_seen=t1, last_seen=t1, occurrences=3),
    }
    incoming = MappingRecord(**fields, first_seen=t2, last_seen=t2, occurrences=2)

    upsert(mapping, key, incoming)

    assert mapping[key].first_seen == t1
    assert mapping[key].last_seen == t2
    assert mapping[key].occurrences == 5


def test_save_mapping_preserves_original_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    t = datetime(2026, 5, 22, 14, 0, 0, tzinfo=UTC)
    fields = {"value": "John Doe", "canonical": "john doe", "type": "name", "id": "p1"}
    mapping_path = tmp_path / "mapping.json"
    save_mapping(
        mapping_path,
        {
            "<NAME:abc>": MappingRecord(
                **fields, first_seen=t, last_seen=t, occurrences=1
            ),
        },
    )
    original_bytes = mapping_path.read_bytes()

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated failure")

    monkeypatch.setattr("os.replace", boom)

    with pytest.raises(OSError, match="simulated failure"):
        save_mapping(
            mapping_path,
            {
                "<NAME:xyz>": MappingRecord(
                    **fields, first_seen=t, last_seen=t, occurrences=99
                ),
            },
        )

    assert mapping_path.read_bytes() == original_bytes
