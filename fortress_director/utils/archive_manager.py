"""Utility helpers for rotating and compressing run/log artifacts."""

from __future__ import annotations

import gzip
import shutil
import time
from pathlib import Path
from typing import Iterable

DEFAULT_MAX_BYTES = 750_000
DEFAULT_KEEP = 5


def rotate_file(
    file_path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    keep: int = DEFAULT_KEEP,
    archive_dir: Path | None = None,
) -> None:
    """Compress *file_path* into ``archive_dir`` when it exceeds *max_bytes*."""

    if not file_path.exists():
        return
    if file_path.stat().st_size <= max_bytes:
        return

    archive_root = archive_dir or file_path.parent / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    archive_name = f"{file_path.stem}_{timestamp}{file_path.suffix}.gz"
    archive_path = archive_root / archive_name

    with file_path.open("rb") as src, gzip.open(archive_path, "wb") as dst:
        shutil.copyfileobj(src, dst)

    file_path.write_text("", encoding="utf-8")
    _prune_archives(archive_root.glob(f"{file_path.stem}_*.gz"), keep)


def compress_pattern(
    directory: Path,
    pattern: str,
    *,
    keep: int = DEFAULT_KEEP,
) -> None:
    """Compress files under *directory* matching *pattern* beyond keep count."""

    directory.mkdir(parents=True, exist_ok=True)
    files = sorted(
        directory.glob(pattern),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for stale in files[keep:]:
        target = stale.with_suffix(stale.suffix + ".gz")
        with stale.open("rb") as src, gzip.open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        stale.unlink(missing_ok=True)


def _prune_archives(archives: Iterable[Path], keep: int) -> None:
    ordered = sorted(
        archives,
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    for extra in ordered[keep:]:
        extra.unlink(missing_ok=True)

