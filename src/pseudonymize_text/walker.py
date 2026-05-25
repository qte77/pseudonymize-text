"""Folder mirror with text-file transformation (ARCHITECTURE.md → walker.py)."""

import os
import shutil
from collections.abc import Callable
from pathlib import Path

WHITELISTED_EXTENSIONS: frozenset[str] = frozenset(
    {".txt", ".md", ".log", ".py", ".json", ".yaml", ".yml", ".csv", ".toml", ".ini"}
)


def walk_and_process(
    in_dir: Path,
    out_dir: Path,
    transform: Callable[[str, Path], str],
) -> None:
    """Mirror ``in_dir`` → ``out_dir`` per ARCHITECTURE.md § Walker behavior.

    Whitelisted extensions are read as UTF-8, passed through ``transform``
    along with their path relative to ``in_dir``, and written to the
    mirrored output path. Other extensions, symlink rules, atomic writes,
    and ``.eml``/``.mbox`` handling land in subsequent Red/Green cycles.
    """
    in_dir = in_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    for src in in_dir.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(in_dir)
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix in WHITELISTED_EXTENSIONS:
            text = src.read_text(encoding="utf-8")
            transformed = transform(text, rel)
            _atomic_write_text(dst, transformed)
        else:
            shutil.copyfile(src, dst)


def _atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` via tmp + ``os.replace``, mode ``0o600``."""
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.replace(tmp, path)
