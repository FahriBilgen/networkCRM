"""Utilities for persisting and loading per-turn trace files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from fortress_director.settings import SETTINGS, ensure_runtime_paths

LOGGER = logging.getLogger(__name__)
TRACE_DIR = Path(SETTINGS.log_dir)


def persist_trace(turn_index: int, payload: Dict[str, Any]) -> Path:
    """Write the structured turn trace to disk and return the file path."""

    ensure_runtime_paths()
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    path = TRACE_DIR / f"turn_{turn_index}.json"
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    path.write_text(serialized, encoding="utf-8")
    final_result = payload.get("final_result")
    if isinstance(final_result, dict):
        persist_final_result(final_result)
    return path


def list_traces(limit: int = 25) -> List[Dict[str, Any]]:
    """Return recent turn traces sorted descending by turn index."""

    if not TRACE_DIR.exists():
        return []
    summaries: List[Dict[str, Any]] = []
    for file in TRACE_DIR.glob("turn_*.json"):
        turn = _parse_turn_from_name(file.name)
        if turn is None:
            continue
        try:
            stat = file.stat()
        except OSError:
            continue
        summaries.append(
            {
                "turn": turn,
                "file": str(file),
                "modified_ts": stat.st_mtime,
            },
        )
    summaries.sort(key=lambda item: item["turn"], reverse=True)
    return summaries[:limit]


def load_trace(turn_index: int) -> Dict[str, Any]:
    """Return the parsed JSON trace for *turn_index*."""

    path = TRACE_DIR / f"turn_{turn_index}.json"
    if not path.exists():
        raise FileNotFoundError(f"Trace for turn {turn_index} not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        LOGGER.error("Failed to parse trace %s: %s", path, exc)
        raise


def _parse_turn_from_name(name: str) -> int | None:
    stem = Path(name).stem
    if "_" not in stem:
        return None
    try:
        return int(stem.split("_", 1)[1])
    except ValueError:
        return None


def persist_final_result(final_result: Dict[str, Any]) -> Path:
    """Persist the final metadata payload to turn_final.json."""

    ensure_runtime_paths()
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    final_path = TRACE_DIR / "turn_final.json"
    serialized = json.dumps(final_result, indent=2, ensure_ascii=False)
    final_path.write_text(serialized, encoding="utf-8")
    return final_path


__all__ = ["persist_trace", "list_traces", "load_trace", "persist_final_result"]
