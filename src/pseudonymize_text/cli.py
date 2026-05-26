"""CLI entry point — `pseudonymize detect` / `pseudonymize apply` (USAGE.md).

Exit codes per USAGE.md § Exit Codes.
"""

import argparse
import hashlib
import hmac
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

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
from .report import ReportWriter
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

    if args.subcommand == "detect":
        return _run_detect(args, key, terms)
    return _run_apply(args, key, terms)


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


def _detect_spans_for_text(text: str, terms: list) -> list[Span]:
    spans: list[Span] = []
    spans.extend(detect_terms(text, terms))
    spans.extend(detect_emails(text))
    spans.extend(detect_phones(text))
    spans.extend(detect_ibans(text))
    spans.extend(detect_credit_cards(text))
    spans.extend(detect_ssns(text))
    return spans


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


def _context(text: str, start: int, end: int, radius: int = 40) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    left = max(line_start, start - radius)
    right = min(line_end, end + radius)
    return text[left:right]


def _run_detect(args: argparse.Namespace, key: bytes, terms: list) -> int:
    """Walk in_dir, detect spans, write a JSONL report. Returns exit code."""
    in_dir = args.in_dir.resolve()
    header = ReportHeader(
        schema="pseudonymize.report/1",
        tool_version=__version__,
        started_at=datetime.now(tz=UTC),
        config_hash=_config_hash(key),
    )
    writer = ReportWriter(args.report, header)
    if args.report.exists():
        args.report.unlink()

    for src in sorted(in_dir.rglob("*")):
        if not src.is_file() or src.suffix not in WHITELISTED_EXTENSIONS:
            continue
        rel = src.relative_to(in_dir).as_posix()
        try:
            text = src.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for span in _detect_spans_for_text(text, terms):
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
    in_dir = args.in_dir.resolve()
    out_dir = args.out_dir
    header = ReportHeader(
        schema="pseudonymize.report/1",
        tool_version=__version__,
        started_at=datetime.now(tz=UTC),
        config_hash=_config_hash(key),
    )
    writer = ReportWriter(args.report, header)
    if args.report.exists():
        args.report.unlink()

    mapping: dict[str, MappingRecord] = {}
    now = datetime.now(tz=UTC)

    def transform(text: str, rel: Path) -> str:
        spans = _detect_spans_for_text(text, terms)
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
        return apply_spans(text, spans, tokens.__getitem__)

    walk_and_process(in_dir, out_dir, transform)
    save_mapping(args.mapping, mapping)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
