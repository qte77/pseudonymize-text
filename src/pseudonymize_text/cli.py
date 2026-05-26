"""CLI entry point — `pseudonymize detect` / `pseudonymize apply` (USAGE.md).

Exit codes per USAGE.md § Exit Codes.
"""

import argparse
import os
import sys
from pathlib import Path

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

    print(
        f"pseudonymize {args.subcommand}: not yet implemented "
        f"(detect/apply pipeline lands in C2..)",
        file=sys.stderr,
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
