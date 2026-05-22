"""JSONL report writer (ARCHITECTURE.md → Report Schema)."""

from pathlib import Path

from ._schemas import ReportHeader, ReportRecord


class ReportWriter:
    """Append-only JSONL writer that emits the header exactly once."""

    def __init__(self, path: Path, header: ReportHeader) -> None:
        """Initialise with the target ``path`` and the run's ``header``."""
        self._path = path
        self._header = header
        self._header_written = False

    def write(self, record: ReportRecord) -> None:
        """Append ``record``; emit the header line on the first call."""
        with self._path.open("a", encoding="utf-8") as fh:
            if not self._header_written:
                fh.write(self._header.model_dump_json(by_alias=True) + "\n")
                self._header_written = True
            fh.write(record.model_dump_json() + "\n")
