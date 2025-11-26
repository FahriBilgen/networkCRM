"""Utilities for loading theme packs from disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .schema import (
    ThemeConfig,
    ThemeEndingSpec,
    ThemeMapSpec,
    ThemeNpcSpec,
)

DATA_DIR = Path(__file__).resolve().parent / "data"
BUILTIN_THEMES = {
    "siege_default": DATA_DIR / "siege_default.json",
    "orbital_outpost": DATA_DIR / "orbital_outpost.json",
}


class ThemeRegistry:
    def __init__(self) -> None:
        self._themes: Dict[str, ThemeConfig] = {}

    def register(self, theme: ThemeConfig) -> None:
        if theme.id in self._themes:
            raise ValueError(f"Theme '{theme.id}' already registered.")
        self._themes[theme.id] = theme

    def get(self, theme_id: str) -> ThemeConfig:
        try:
            return self._themes[theme_id]
        except KeyError as exc:
            raise KeyError(f"Theme '{theme_id}' is not registered.") from exc

    def list_ids(self) -> List[str]:
        return sorted(self._themes.keys())


def load_theme_from_file(path: str | Path) -> ThemeConfig:
    theme_path = Path(path)
    if not theme_path.exists():
        raise FileNotFoundError(theme_path)
    try:
        payload = json.loads(theme_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - invalid file
        raise ValueError(f"Invalid JSON in {theme_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Theme config must be a JSON object.")

    theme_id = _require_str(payload, "id")
    label = _require_str(payload, "label")
    description = _require_str(payload, "description")
    map_payload = payload.get("map")
    if not isinstance(map_payload, dict):
        raise ValueError("Theme map spec must be an object.")
    map_spec = ThemeMapSpec(
        width=_require_int(map_payload, "width"),
        height=_require_int(map_payload, "height"),
        layout=_parse_layout(map_payload.get("layout")),
    )
    npcs = _parse_npcs(payload.get("npcs"))
    initial_metrics = payload.get("initial_metrics") or {}
    if not isinstance(initial_metrics, dict):
        raise ValueError("initial_metrics must be an object.")
    event_graph_file = _resolve_path(theme_path, payload.get("event_graph_file"))
    safe_function_overrides = payload.get("safe_function_overrides") or {}
    if not isinstance(safe_function_overrides, dict):
        raise ValueError("safe_function_overrides must be an object if provided.")
    endings = _parse_endings(payload.get("endings"))

    overrides: Dict[str, Dict[str, object]] = {}
    for name, config in safe_function_overrides.items():
        if not isinstance(config, dict):
            raise ValueError("safe_function_overrides entries must be objects.")
        overrides[str(name)] = dict(config)

    return ThemeConfig(
        id=theme_id,
        label=label,
        description=description,
        map=map_spec,
        npcs=npcs,
        initial_metrics=dict(initial_metrics),
        event_graph_file=event_graph_file,
        safe_function_overrides=overrides,
        endings=endings,
    )


def load_builtin_themes() -> ThemeRegistry:
    registry = ThemeRegistry()
    for theme_id, path in BUILTIN_THEMES.items():
        theme = load_theme_from_file(path)
        if theme.id != theme_id:
            raise ValueError(
                f"Theme file {path} has mismatched id '{theme.id}' (expected {theme_id})."
            )
        registry.register(theme)
    return registry


def _parse_layout(payload: object) -> List[List[str]]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("map.layout must be an array.")
    layout: List[List[str]] = []
    for row in payload:
        if not isinstance(row, list):
            raise ValueError("map.layout rows must be arrays.")
        layout.append([str(cell) for cell in row])
    return layout


def _parse_npcs(payload: object) -> List[ThemeNpcSpec]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("npcs must be an array.")
    result: List[ThemeNpcSpec] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("Each NPC entry must be an object.")
        raw_tags = entry.get("tags") or []
        if not isinstance(raw_tags, list):
            raise ValueError("npc.tags must be an array when provided.")
        result.append(
            ThemeNpcSpec(
                id=_require_str(entry, "id"),
                name=_require_str(entry, "name"),
                role=_require_str(entry, "role"),
                x=_require_int(entry, "x"),
                y=_require_int(entry, "y"),
                tags=[str(tag) for tag in raw_tags],
            )
        )
    return result


def _parse_endings(payload: object) -> List[ThemeEndingSpec]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("endings must be an array.")
    results: List[ThemeEndingSpec] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("Each ending entry must be an object.")
        conditions = entry.get("conditions") or {}
        if not isinstance(conditions, dict):
            raise ValueError("ending conditions must be an object.")
        results.append(
            ThemeEndingSpec(
                id=_require_str(entry, "id"),
                label=_require_str(entry, "label"),
                conditions=dict(conditions),
            )
        )
    return results


def _require_str(payload: Dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"{key} must be a non-empty string.")
    return value


def _require_int(payload: Dict[str, object], key: str) -> int:
    value = payload.get(key)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be an integer.") from None


def _resolve_path(base_file: Path, reference: object) -> str:
    if not isinstance(reference, str):
        raise ValueError("event_graph_file must be a string path.")
    ref_path = Path(reference)
    if not ref_path.is_absolute():
        ref_path = base_file.parent / ref_path
    return str(ref_path)


__all__ = [
    "BUILTIN_THEMES",
    "DATA_DIR",
    "ThemeRegistry",
    "load_builtin_themes",
    "load_theme_from_file",
]
