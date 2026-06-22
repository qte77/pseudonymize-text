"""JSONL + TSV report writers (ARCHITECTURE.md → Report Schema)."""

from pathlib import Path

from ._schemas import ReportHeader, ReportRecord

_TSV_COLUMNS: tuple[str, ...] = (
    "file", "line", "col", "start", "end", "text", "detector",
    "type", "id", "token", "confidence", "context",
)
_FORMULA_LEAD: frozenset[str] = frozenset({"=", "+", "-", "@"})


def _tsv_cell(value: object) -> str:
    """Stringify ``value`` for TSV: collapse tab/newline, prefix formulas."""
    text = "" if value is None else str(value)
    text = text.replace("\t", " ").replace("\n", " ").replace("\r", " ")
    if text and text[0] in _FORMULA_LEAD:
        text = "'" + text
    return text


class ReportWriter:
    """Append-only JSONL writer that emits the header exactly once."""

    def __init__(self, path: Path, header: ReportHeader) -> None:
        """Initialise with the target ``path`` and the run's ``header``."""
        self._path = path
        self._header = header
        self._header_written = False

    def write_header(self) -> None:
        """Emit the header line if it has not been written yet (idempotent).

        Lets ``detect`` produce a valid header-only report when zero spans are
        found, so a later ``apply --plan`` reads an empty plan instead of
        failing on a missing file.
        """
        if self._header_written:
            return
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(self._header.model_dump_json(by_alias=True) + "\n")
        self._header_written = True

    def write(self, record: ReportRecord) -> None:
        """Append ``record``; emit the header line on the first call."""
        self.write_header()
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(record.model_dump_json() + "\n")


class TsvReportWriter:
    """Append-only TSV writer with formula-injection prefix on every cell.

    First line is a `# ` comment carrying the run header fields
    (schema/tool_version/config_hash) so the audit trail isn't lost.
    Second line is the column-name row. Records follow.
    """

    def __init__(self, path: Path, header: ReportHeader) -> None:
        """Initialise with the target ``path`` and the run's ``header``."""
        self._path = path
        self._header = header
        self._header_written = False

    def write_header(self) -> None:
        """Emit the ``# `` meta comment + column row if not yet written.

        Idempotent; lets a zero-span ``detect`` leave a valid header-only TSV
        report (see ``ReportWriter.write_header``).
        """
        if self._header_written:
            return
        with self._path.open("a", encoding="utf-8") as fh:
            meta = self._header.model_dump(by_alias=True, mode="json")
            meta_pairs = " ".join(f"{k}={v}" for k, v in meta.items())
            fh.write(f"# {meta_pairs}\n")
            fh.write("\t".join(_TSV_COLUMNS) + "\n")
        self._header_written = True

    def write(self, record: ReportRecord) -> None:
        """Append ``record``; emit header + column row on first call."""
        self.write_header()
        with self._path.open("a", encoding="utf-8") as fh:
            row = record.model_dump(mode="json")
            fh.write(
                "\t".join(_tsv_cell(row.get(col)) for col in _TSV_COLUMNS) + "\n"
            )
