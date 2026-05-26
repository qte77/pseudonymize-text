"""Tests for cli.py (issue #13)."""

from pathlib import Path

import pytest

from pseudonymize_text.cli import main


def test_cli_no_args_exits_with_usage_error() -> None:
    assert main([]) == 2


def test_cli_unknown_subcommand_exits_with_usage_error() -> None:
    assert main(["totally-unknown"]) == 2


def test_cli_detect_without_in_dir_exits_with_usage_error() -> None:
    assert main(["detect"]) == 2


def test_cli_detect_missing_key_exits_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    monkeypatch.delenv("PSEUDONYMIZE_KEY", raising=False)
    assert main(["detect", str(in_dir), "--no-terms"]) == 3


def test_cli_apply_mapping_inside_out_dir_exits_7(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text("hi", encoding="utf-8")
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)
    bad_mapping = out_dir / "mapping.json"
    rc = main(
        [
            "apply", str(in_dir), str(out_dir),
            "--no-terms",
            "--mapping", str(bad_mapping),
        ]
    )
    assert rc == 7
    assert not out_dir.exists() or not bad_mapping.exists()


def test_cli_apply_report_inside_out_dir_exits_7(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text("hi", encoding="utf-8")
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)
    bad_report = out_dir / "report.jsonl"
    rc = main(
        [
            "apply", str(in_dir), str(out_dir),
            "--no-terms",
            "--report", str(bad_report),
        ]
    )
    assert rc == 7


def test_cli_apply_ignore_file_with_unicode_cleanup_suppresses_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text(
        "Visit Straße for the meeting", encoding="utf-8"
    )
    terms = tmp_path / "terms.csv"
    terms.write_text("value,type\nStraße,loc\n", encoding="utf-8")
    ignore = tmp_path / "ignore.txt"
    # Zero-width space inside the entry must be stripped by NFKC + Cf cleanup.
    ignore.write_text("Stras​se\n", encoding="utf-8")
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    rc = main(
        [
            "apply", str(in_dir), str(tmp_path / "out"),
            "--terms", str(terms),
            "--ignore", str(ignore),
            "--mapping", str(tmp_path / "mapping.json"),
            "--report", str(tmp_path / "report.jsonl"),
        ]
    )

    assert rc == 0
    written = (tmp_path / "out" / "a.txt").read_text(encoding="utf-8")
    # Ignore entry "Stras​se" → NFKC+casefold+Cf-strip → "strasse"
    # → equals casefold(NFKC("Straße")) so the span is suppressed.
    assert "Straße" in written
    assert "<LOC:" not in written


def test_cli_detectors_filter_excludes_structured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text(
        "Email alice@acme.com; name John Doe", encoding="utf-8"
    )
    terms = tmp_path / "terms.csv"
    terms.write_text("value,type\nJohn Doe,name\n", encoding="utf-8")
    report = tmp_path / "r.jsonl"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    rc = main(
        [
            "detect", str(in_dir),
            "--terms", str(terms),
            "--detectors", "literal",
            "--report", str(report),
        ]
    )
    assert rc == 0
    import json as _json

    records = [_json.loads(line) for line in report.read_text().splitlines()[1:]]
    detectors_used = {r["detector"] for r in records}
    assert detectors_used == {"literal"}
    assert any(r["text"] == "John Doe" for r in records)


def test_cli_types_filter_keeps_only_named_types(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text(
        "Email alice@acme.com; SSN 123-45-6789", encoding="utf-8"
    )
    report = tmp_path / "r.jsonl"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    rc = main(
        [
            "detect", str(in_dir),
            "--no-terms",
            "--types", "email",
            "--report", str(report),
        ]
    )
    assert rc == 0
    import json as _json

    records = [_json.loads(line) for line in report.read_text().splitlines()[1:]]
    types_seen = {r["type"] for r in records}
    assert types_seen == {"email"}


def test_cli_ner_flag_off_by_default_does_not_invoke_spacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --ner, spacy is never imported even if installed."""
    import sys

    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text("Some text", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "spacy", None)
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    rc = main(
        [
            "detect", str(in_dir), "--no-terms",
            "--report", str(tmp_path / "r.jsonl"),
        ]
    )
    # If --ner were on, the import would fail with ExitCode 5 because spacy
    # is shadowed to None. Off-by-default means rc=0.
    assert rc == 0


def test_cli_detect_tsv_format_writes_header_and_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text(
        "Mail alice@acme.com today", encoding="utf-8"
    )
    report = tmp_path / "report.tsv"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    rc = main(
        [
            "detect", str(in_dir),
            "--no-terms",
            "--report", str(report),
            "--report-format", "tsv",
        ]
    )
    assert rc == 0
    lines = report.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# "), "first line is the metadata comment"
    columns = lines[1].split("\t")
    assert "text" in columns
    assert "context" in columns
    assert any("alice@acme.com" in line for line in lines[2:])
    # Every data cell that begins with a formula char must be prefixed.
    for line in lines[2:]:
        for cell in line.split("\t"):
            assert not cell.startswith(("=", "+", "-", "@")), (
                f"unprefixed formula-leading cell: {cell!r}"
            )


def test_cli_detect_context_strips_bidi_and_zero_width(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    # ZWSP + RLO around an email; both must be stripped from `context`
    # before the record is written.
    (in_dir / "a.txt").write_text(
        "Contact ​‮alice@acme.com‬ soon", encoding="utf-8"
    )
    report = tmp_path / "r.jsonl"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    rc = main(
        ["detect", str(in_dir), "--no-terms", "--report", str(report)]
    )
    assert rc == 0
    import json as _json

    records = [_json.loads(line) for line in report.read_text().splitlines()[1:]]
    assert records, "expected at least one record"
    for r in records:
        for bad in ("​", "‬", "‭", "‮"):
            assert bad not in r["context"], f"{bad!r} survived in context"


def test_cli_detect_oversize_file_exits_6(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "huge.txt").write_text("x" * 1024, encoding="utf-8")
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)
    monkeypatch.setenv("PSEUDONYMIZE_MAX_FILE_BYTES", "10")

    rc = main(
        ["detect", str(in_dir), "--no-terms", "--report", str(tmp_path / "r.jsonl")]
    )
    assert rc == 6


def test_cli_apply_with_plan_uses_only_plan_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text(
        "alice@acme.com and bob@acme.com", encoding="utf-8"
    )
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    # First, generate a full plan via detect.
    full_plan = tmp_path / "full-plan.jsonl"
    assert (
        main(["detect", str(in_dir), "--no-terms", "--report", str(full_plan)])
        == 0
    )
    lines = full_plan.read_text(encoding="utf-8").splitlines()
    # Header + 2 records (alice + bob); keep only the alice record.
    header, *records = lines
    alice_record = next(r for r in records if "alice@acme.com" in r)
    edited_plan = tmp_path / "alice-only.jsonl"
    edited_plan.write_text(header + "\n" + alice_record + "\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    mapping = tmp_path / "mapping.json"
    report = tmp_path / "report.jsonl"
    rc = main(
        [
            "apply", str(in_dir), str(out_dir),
            "--no-terms",
            "--plan", str(edited_plan),
            "--mapping", str(mapping),
            "--report", str(report),
        ]
    )
    assert rc == 0
    written = (out_dir / "a.txt").read_text(encoding="utf-8")
    # Plan listed only alice → only alice substituted; bob passes through.
    assert "alice@acme.com" not in written
    assert "bob@acme.com" in written
    assert "<EMAIL:" in written


def test_cli_apply_plan_config_hash_mismatch_exits_7(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text("Hi alice@acme.com", encoding="utf-8")
    plan = tmp_path / "plan.jsonl"

    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)
    assert main(["detect", str(in_dir), "--no-terms", "--report", str(plan)]) == 0

    # Different key → different config_hash → exit 7.
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "cd" * 32)
    out_dir = tmp_path / "out"
    rc = main(
        [
            "apply", str(in_dir), str(out_dir),
            "--no-terms", "--plan", str(plan),
        ]
    )
    assert rc == 7


def test_cli_apply_plan_path_traversal_exits_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    # Build a plan with a malicious file field.
    plan = tmp_path / "evil.jsonl"
    plan.write_text(
        '{"schema":"pseudonymize.report/1","tool_version":"x","'
        'started_at":"2026-05-26T00:00:00Z","config_hash":"'
        + ("0" * 32) + '"}\n'
        '{"file":"../../etc/passwd","line":1,"col":1,"start":0,'
        '"end":3,"text":"abc","detector":"literal","type":"name",'
        '"id":null,"token":"<NAME:' + ("0" * 32) + '>",'
        '"confidence":null,"context":"abc"}\n',
        encoding="utf-8",
    )

    rc = main(
        [
            "apply", str(in_dir), str(tmp_path / "out"),
            "--no-terms", "--plan", str(plan),
        ]
    )
    assert rc == 4


def test_cli_apply_writes_substituted_output_and_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text(
        "Contact alice@acme.com soon", encoding="utf-8"
    )
    mapping = tmp_path / "mapping.json"
    report = tmp_path / "report.jsonl"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    rc = main(
        [
            "apply", str(in_dir), str(out_dir),
            "--no-terms",
            "--mapping", str(mapping),
            "--report", str(report),
        ]
    )

    assert rc == 0
    written = (out_dir / "a.txt").read_text(encoding="utf-8")
    assert "alice@acme.com" not in written
    assert "<EMAIL:" in written
    assert mapping.exists()
    assert "alice@acme.com" in mapping.read_text(encoding="utf-8")


def test_cli_detect_writes_report_with_header_and_spans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "a.txt").write_text(
        "Contact alice@acme.com about the order", encoding="utf-8"
    )
    report = tmp_path / "report.jsonl"
    monkeypatch.setenv("PSEUDONYMIZE_KEY", "ab" * 32)

    rc = main(
        ["detect", str(in_dir), "--no-terms", "--report", str(report)]
    )

    assert rc == 0
    lines = report.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 2
    assert "pseudonymize.report/1" in lines[0]
    assert "alice@acme.com" in "\n".join(lines[1:])
