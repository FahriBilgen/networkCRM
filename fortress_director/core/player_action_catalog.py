"""Loader for the player action catalog (YAML) providing a normalized dict list."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_CATALOG_PATH = Path(__file__).parent / "player_actions.yaml"


def _normalize_entry(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(raw.get("id")),
        "label": str(raw.get("label") or ""),
        "requires": list(raw.get("requires") or []),
        "safe_function": str(raw.get("safe_function") or ""),
        "args_map": dict(raw.get("args_map") or {}),
    }


@lru_cache(maxsize=1)
def load_actions() -> List[Dict[str, Any]]:
    """Load and return the player action catalog as a list of normalized dicts.

    The result is cached for the process lifetime.
    """
    if not _CATALOG_PATH.exists():
        return []
    text = _CATALOG_PATH.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(text)
    except Exception:
        # Return empty on parse error to avoid hard failures in environments
        return []
    if not isinstance(raw, list):
        return []
    return [_normalize_entry(entry) for entry in raw if isinstance(entry, dict)]


def get_action_by_id(action_id: str) -> Optional[Dict[str, Any]]:
    for entry in load_actions():
        if entry.get("id") == action_id:
            return entry
    return None


def dump_catalog() -> str:
    """Return JSON representation (debug) of the loaded catalog."""
    return json.dumps(load_actions(), ensure_ascii=False)
