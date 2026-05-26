"""CLI entry point — `pseudonymize detect` / `pseudonymize apply` (USAGE.md).

Exit codes per USAGE.md § Exit Codes.
"""

import argparse
import hashlib
import hmac
import os
import sys
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from . import __version__
from ._schemas import MappingRecord, ReportHeader, ReportRecord
from .detectors.structured import (
    detect_credit_cards,
    detect_emails,
    detect_ibans,
    detect_phones,
    detect_ssns,
)
from .detectors.terms import detect_terms, load_terms
from .mapping import save_mapping, upsert
from .replacer import Span, apply_spans
from .report import ReportWriter, TsvReportWriter
from .tokenize import canonicalize, hmac_token
from .walker import WHITELISTED_EXTENSIONS, walk_and_process

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_KEY = 3
EXIT_TERMS = 4
EXIT_DETECTOR = 5
EXIT_IO = 6
EXIT_PATH_SAFETY = 7


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pseudonymize")
    subs = parser.add_subparsers(dest="subcommand", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--terms", type=Path)
    common.add_argument("--no-terms", action="store_true")
    common.add_argument("--key-file", type=Path)
    common.add_argument("--report", type=Path, default=Path("./pseudonymize-report.jsonl"))
    common.add_argument(
        "--report-format", choices=("jsonl", "tsv"), default="jsonl"
    )
    common.add_argument("--ignore", type=Path)
    common.add_argument(
        "--detectors",
        default="literal,structured",
        help="comma list: literal, structured, ner",
    )
    common.add_argument(
        "--types",
        default="name,email,phone,iban,cc,ssn,org,loc",
        help="comma list of entity types to keep",
    )
    common.add_argument("--ner", action="store_true", help="enable NER (requires [ner] extra)")

    detect = subs.add_parser("detect", parents=[common])
    detect.add_argument("in_dir", type=Path)

    apply_p = subs.add_parser("apply", parents=[common])
    apply_p.add_argument("in_dir", type=Path)
    apply_p.add_argument("out_dir", type=Path)
    apply_p.add_argument(
        "--mapping", type=Path, default=Path("./pseudonymize-mapping.json")
    )
    apply_p.add_argument("--plan", type=Path)

    return parser


def _resolve_key(args: argparse.Namespace) -> bytes | None:
    if args.key_file is not None:
        try:
            return bytes.fromhex(args.key_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None
    env = os.environ.get("PSEUDONYMIZE_KEY")
    if env:
        try:
            return bytes.fromhex(env.strip())
        except ValueError:
            return None
    return None


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns an exit code per USAGE.md § Exit Codes."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else EXIT_USAGE

    key = _resolve_key(args)
    if key is None:
        print(
            "error: HMAC key not found; set PSEUDONYMIZE_KEY or pass --key-file PATH",
            file=sys.stderr,
        )
        return EXIT_KEY

    terms_or_rc = _load_terms_or_rc(args)
    if isinstance(terms_or_rc, int):
        return terms_or_rc
    terms = terms_or_rc

    ignore_or_rc = _load_ignore_or_rc(args)
    if isinstance(ignore_or_rc, int):
        return ignore_or_rc
    args.ignore_entries = ignore_or_rc

    args.enabled_detectors = {d.strip() for d in args.detectors.split(",") if d.strip()}
    if args.ner:
        args.enabled_detectors.add("ner")
    args.enabled_types = {t.strip() for t in args.types.split(",") if t.strip()}

    if args.subcommand == "apply":
        path_safety = _check_apply_path_safety(args)
        if path_safety != EXIT_OK:
            return path_safety
        return _run_apply(args, key, terms)
    return _run_detect(args, key, terms)


def _clean_ignore_entry(entry: str) -> str:
    """NFKC + casefold + strip Unicode `Cf` and non-ASCII `Zs` per #7 spec."""
    nfkc = unicodedata.normalize("NFKC", entry)
    out: list[str] = []
    for ch in nfkc:
        cat = unicodedata.category(ch)
        if cat == "Cf":
            continue
        if cat == "Zs" and ch != " ":
            continue
        out.append(ch)
    return "".join(out).casefold().strip()


def _load_ignore_or_rc(args: argparse.Namespace) -> list[str] | int:
    """Read ``--ignore`` line-by-line, NFKC + strip-format-chars per entry."""
    if args.ignore is None:
        return []
    try:
        raw = args.ignore.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: --ignore {args.ignore}: {exc}", file=sys.stderr)
        return EXIT_TERMS
    out: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append(_clean_ignore_entry(stripped))
    return out


def _is_under(path: Path, parent: Path) -> bool:
    """True iff ``path`` resolves under ``parent`` (after both are resolved)."""
    try:
        return path.resolve().is_relative_to(parent.resolve())
    except (OSError, ValueError):
        return False


def _check_apply_path_safety(args: argparse.Namespace) -> int:
    """Return EXIT_PATH_SAFETY if --mapping or --report is inside out_dir."""
    out_dir = args.out_dir
    for label, candidate in (("--mapping", args.mapping), ("--report", args.report)):
        if _is_under(candidate, out_dir):
            print(
                f"error: {label} {candidate} would land inside <out_dir> {out_dir}; "
                "see SECURITY.md § Operational rules",
                file=sys.stderr,
            )
            return EXIT_PATH_SAFETY
    return EXIT_OK


def _load_plan_or_rc(
    args: argparse.Namespace, key: bytes
) -> tuple[ReportHeader, dict[str, list[Span]]] | int:
    """Parse the ``--plan`` JSONL, validate config_hash + path safety.

    Returns ``(header, spans_by_relpath)`` on success, an exit code on
    error (4 = unparseable / traversal, 7 = config_hash mismatch).
    """
    try:
        text = args.plan.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: --plan {args.plan}: {exc}", file=sys.stderr)
        return EXIT_TERMS
    lines = text.splitlines()
    if not lines:
        return EXIT_TERMS
    try:
        header = ReportHeader.model_validate_json(lines[0])
        records = [ReportRecord.model_validate_json(line) for line in lines[1:]]
    except (ValidationError, ValueError) as exc:
        print(f"error: --plan {args.plan}: {exc}", file=sys.stderr)
        return EXIT_TERMS
    # Validate structure (paths) before crypto (config_hash) so a
    # malformed plan exits 4 regardless of whose key it was signed under.
    in_dir = args.in_dir.resolve()
    spans_by_file: dict[str, list[Span]] = {}
    for record in records:
        parts = Path(record.file).parts
        if Path(record.file).is_absolute() or ".." in parts:
            print(
                f"error: --plan record file {record.file!r} contains "
                "forbidden traversal",
                file=sys.stderr,
            )
            return EXIT_TERMS
        if not (in_dir / record.file).resolve().is_relative_to(in_dir):
            print(
                f"error: --plan record file {record.file!r} resolves outside "
                f"<in_dir>",
                file=sys.stderr,
            )
            return EXIT_TERMS
        spans_by_file.setdefault(record.file, []).append(
            Span(
                start=record.start,
                end=record.end,
                text=record.text,
                type=record.type,
                detector=record.detector,
                id=record.id,
                confidence=record.confidence,
            )
        )
    if header.config_hash != _config_hash(key):
        print(
            "error: --plan config_hash does not match current key fingerprint; "
            "the plan was produced with a different key or detector set",
            file=sys.stderr,
        )
        return EXIT_PATH_SAFETY
    return header, spans_by_file


def _load_terms_or_rc(args: argparse.Namespace) -> list | int:
    """Return a parsed term list, or an exit code on error."""
    if args.no_terms or args.terms is None:
        return []
    try:
        return load_terms(args.terms)
    except (ValueError, OSError) as exc:
        print(f"error: --terms {args.terms}: {exc}", file=sys.stderr)
        return EXIT_TERMS


def _config_hash(key: bytes) -> str:
    """16-byte (32-hex) fingerprint of ``key`` per HASHING.md truncation rule."""
    return hmac.new(key, b"pseudonymize-key-fingerprint-v1", hashlib.sha256).hexdigest()[:32]


_STRUCTURED_DISPATCH = {
    "email": detect_emails,
    "phone": detect_phones,
    "iban": detect_ibans,
    "cc": detect_credit_cards,
    "ssn": detect_ssns,
}


def _detect_spans_for_text(
    text: str,
    terms: list,
    enabled_detectors: set[str],
    enabled_types: set[str],
) -> list[Span]:
    spans: list[Span] = []
    if "literal" in enabled_detectors:
        spans.extend(detect_terms(text, terms))
    if "structured" in enabled_detectors:
        for type_, fn in _STRUCTURED_DISPATCH.items():
            if type_ in enabled_types:
                spans.extend(fn(text))
    if "ner" in enabled_detectors:
        from .detectors.ner import detect_ner  # lazy import

        spans.extend(detect_ner(text))
    return [s for s in spans if s.type in enabled_types]


def _token_for(span: Span, key: bytes) -> str:
    type_upper = span.type.upper()
    if span.id is not None:
        return hmac_token(key, type_upper, "id", span.id)
    return hmac_token(key, type_upper, "v", canonicalize(span.text, span.type))


def _line_col(text: str, offset: int) -> tuple[int, int]:
    prefix = text[:offset]
    line = prefix.count("\n") + 1
    col = offset - (prefix.rfind("\n") + 1) + 1
    return line, col


_BIDI_AND_ZW: frozenset[str] = frozenset(
    chr(c) for c in (
        *range(0x200B, 0x2010),  # ZWSP, ZWNJ, ZWJ, LRM, RLM, LRE, RLE, PDF, LRO
        0x202A, 0x202B, 0x202C, 0x202D, 0x202E,  # LRE/RLE/PDF/LRO/RLO
        *range(0x2060, 0x206A),  # word joiner, function application, etc.
    )
)


def _strip_bidi(text: str) -> str:
    """Strip bidi-override and zero-width chars from display strings."""
    if not any(ch in _BIDI_AND_ZW for ch in text):
        return text
    return "".join(ch for ch in text if ch not in _BIDI_AND_ZW)


def _context(text: str, start: int, end: int, radius: int = 40) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    left = max(line_start, start - radius)
    right = min(line_end, end + radius)
    return _strip_bidi(text[left:right])


def _max_file_bytes() -> int:
    """Per-file size cap; ``PSEUDONYMIZE_MAX_FILE_BYTES`` overrides default (256 MB)."""
    env = os.environ.get("PSEUDONYMIZE_MAX_FILE_BYTES")
    if env is not None:
        try:
            return int(env)
        except ValueError:
            return 256 * 1024 * 1024
    return 256 * 1024 * 1024


def _make_report_writer(
    args: argparse.Namespace, header: ReportHeader
) -> "ReportWriter | TsvReportWriter":
    if args.report_format == "tsv":
        return TsvReportWriter(args.report, header)
    return ReportWriter(args.report, header)


def _run_detect(args: argparse.Namespace, key: bytes, terms: list) -> int:
    """Walk in_dir, detect spans, write a JSONL report. Returns exit code."""
    in_dir = args.in_dir.resolve()
    header = ReportHeader(
        schema="pseudonymize.report/1",
        tool_version=__version__,
        started_at=datetime.now(tz=UTC),
        config_hash=_config_hash(key),
    )
    if args.report.exists():
        args.report.unlink()
    writer = _make_report_writer(args, header)
    max_bytes = _max_file_bytes()

    for src in sorted(in_dir.rglob("*")):
        if not src.is_file() or src.suffix not in WHITELISTED_EXTENSIONS:
            continue
        try:
            size = src.stat().st_size
        except OSError:
            continue
        if size > max_bytes:
            print(
                f"error: {src} is {size} bytes; exceeds "
                f"PSEUDONYMIZE_MAX_FILE_BYTES={max_bytes}",
                file=sys.stderr,
            )
            return EXIT_IO
        rel = src.relative_to(in_dir).as_posix()
        try:
            text = src.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for span in _detect_spans_for_text(
            text, terms, args.enabled_detectors, args.enabled_types
        ):
            line, col = _line_col(text, span.start)
            writer.write(
                ReportRecord(
                    file=rel,
                    line=line,
                    col=col,
                    start=span.start,
                    end=span.end,
                    text=span.text,
                    detector=span.detector,
                    type=span.type,
                    id=span.id,
                    token=_token_for(span, key),
                    confidence=span.confidence,
                    context=_context(text, span.start, span.end),
                )
            )
    return EXIT_OK


def _run_apply(args: argparse.Namespace, key: bytes, terms: list) -> int:
    """Walk in_dir → out_dir, substitute spans with tokens, persist mapping + report."""
    plan_spans: dict[str, list[Span]] = {}
    if args.plan is not None:
        loaded = _load_plan_or_rc(args, key)
        if isinstance(loaded, int):
            return loaded
        _, plan_spans = loaded

    in_dir = args.in_dir.resolve()
    out_dir = args.out_dir
    header = ReportHeader(
        schema="pseudonymize.report/1",
        tool_version=__version__,
        started_at=datetime.now(tz=UTC),
        config_hash=_config_hash(key),
    )
    if args.report.exists():
        args.report.unlink()
    writer = _make_report_writer(args, header)

    mapping: dict[str, MappingRecord] = {}
    now = datetime.now(tz=UTC)

    def transform(text: str, rel: Path) -> str:
        if args.plan is not None:
            spans = plan_spans.get(rel.as_posix(), [])
        else:
            spans = _detect_spans_for_text(
                text, terms, args.enabled_detectors, args.enabled_types
            )
        tokens = {span: _token_for(span, key) for span in spans}
        for span, token in tokens.items():
            upsert(
                mapping,
                token,
                MappingRecord(
                    value=span.text,
                    canonical=canonicalize(span.text, span.type),
                    type=span.type,
                    id=span.id,
                    first_seen=now,
                    last_seen=now,
                    occurrences=1,
                ),
            )
            line, col = _line_col(text, span.start)
            writer.write(
                ReportRecord(
                    file=rel.as_posix(),
                    line=line,
                    col=col,
                    start=span.start,
                    end=span.end,
                    text=span.text,
                    detector=span.detector,
                    type=span.type,
                    id=span.id,
                    token=token,
                    confidence=span.confidence,
                    context=_context(text, span.start, span.end),
                )
            )
        return apply_spans(
            text, spans, tokens.__getitem__, ignore=args.ignore_entries
        )

    walk_and_process(in_dir, out_dir, transform)
    save_mapping(args.mapping, mapping)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
