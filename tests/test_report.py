from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from pseudonymize_text._schemas import ReportHeader, ReportRecord
from pseudonymize_text.report import ReportWriter, TsvReportWriter


def _header() -> ReportHeader:
    return ReportHeader(
        schema="pseudonymize.report/1",
        tool_version="0.0.1",
        started_at=datetime(2026, 5, 22, 14, 0, 0, tzinfo=UTC),
        config_hash="deadbeefcafef00d0123456789abcdef",
    )


def _record() -> ReportRecord:
    return ReportRecord(
        file="logs/app.log",
        line=1,
        col=1,
        start=0,
        end=8,
        text="John Doe",
        detector="literal",
        type="name",
        id="p1",
        token="<NAME:d273039bdb37a853c53f592bb1b460e0>",
        confidence=None,
        context="John Doe",
    )


def test_report_header_config_hash_rejects_non_hex() -> None:
    with pytest.raises(ValidationError):
        ReportHeader(
            schema="pseudonymize.report/1",
            tool_version="0.0.1",
            started_at=datetime(2026, 5, 22, 14, 0, 0, tzinfo=UTC),
            config_hash="not-hex",
        )


def test_report_writer_writes_header_once(tmp_path: Path) -> None:
    writer = ReportWriter(tmp_path / "report.jsonl", _header())
    writer.write(_record())
    writer.write(_record())

    lines = (tmp_path / "report.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert "tool_version" in lines[0]
    assert "tool_version" not in lines[1]
    assert "tool_version" not in lines[2]


def test_tsv_report_writer_prefixes_formula_cells(tmp_path: Path) -> None:
    """Cells whose first char is = + - @ must be prefixed with a single quote."""
    path = tmp_path / "report.tsv"
    writer = TsvReportWriter(path, _header())
    writer.write(
        ReportRecord(
            file="logs/app.log",
            line=1,
            col=1,
            start=0,
            end=8,
            text="=cmd|' /C calc'!A0",
            detector="literal",
            type="name",
            id="p1",
            token="<NAME:d273039bdb37a853c53f592bb1b460e0>",
            confidence=None,
            context="@SUM(A1:A9)",
        )
    )
    lines = path.read_text(encoding="utf-8").splitlines()
    # 0: meta comment, 1: column row, 2: data row
    assert lines[0].startswith("# ")
    columns = lines[1].split("\t")
    cells = lines[2].split("\t")
    by_col = dict(zip(columns, cells, strict=True))
    assert by_col["text"] == "'=cmd|' /C calc'!A0"
    assert by_col["context"] == "'@SUM(A1:A9)"
