from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from fortress_director.settings import SETTINGS


class ThemeError(RuntimeError):
    """Raised when a theme package cannot be loaded or validated."""


@dataclass(frozen=True)
class ThemeConfig:
    """Normalized view of a theme package."""

    id: str
    label: str
    description: str
    version: int
    prompt_paths: Dict[str, Path]
    world_overrides: Dict[str, Any]
    safe_function_overrides: Dict[str, Any]
    assets: Dict[str, Any]
    raw: Dict[str, Any]
    source_path: Path


THEMES_ROOT = SETTINGS.project_root.parent / "themes"


def load_theme_package(identifier: str) -> ThemeConfig:
    """Load a theme JSON (by id or path) and normalize overrides."""

    path = _resolve_theme_path(identifier)
    data = _load_with_inheritance(path, stack=[])
    return _normalize_theme(data, path)


def build_world_state_for_theme(
    theme: ThemeConfig,
    base_state: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply world_state overrides onto DEFAULT_WORLD_STATE."""

    themed_state = deepcopy(base_state)
    _deep_merge(themed_state, deepcopy(theme.world_overrides))
    themed_state["theme_id"] = theme.id
    themed_state["theme_label"] = theme.label
    return themed_state


def _resolve_theme_path(identifier: str) -> Path:
    candidate = Path(identifier)
    if candidate.is_file():
        return candidate
    suffix = "" if identifier.endswith(".json") else ".json"
    by_id = THEMES_ROOT / f"{identifier}{suffix}"
    if by_id.is_file():
        return by_id
    raise ThemeError(f"Theme '{identifier}' not found (expected {candidate} or {by_id}).")


def _load_with_inheritance(path: Path, stack: list[Path]) -> Dict[str, Any]:
    if path in stack:
        cycle = " -> ".join(p.stem for p in stack + [path])
        raise ThemeError(f"Cyclic theme inheritance detected: {cycle}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ThemeError(f"Failed to parse theme file {path}: {exc}") from exc
    inherits = payload.get("inherits")
    if inherits:
        parent_path = _resolve_theme_path(str(inherits))
        parent = _load_with_inheritance(parent_path, stack + [path])
        merged = deepcopy(parent)
        _deep_merge(merged, payload)
        return merged
    return payload


def _normalize_theme(data: Dict[str, Any], path: Path) -> ThemeConfig:
    theme_id = str(data.get("id") or path.stem)
    label = str(data.get("label") or theme_id)
    description = str(data.get("description") or "")
    try:
        version = int(data.get("version", 1))
    except (TypeError, ValueError) as exc:
        raise ThemeError(f"Theme '{theme_id}' has invalid version: {exc}") from exc

    prompt_paths = _normalize_prompt_paths(
        data.get("prompt_overrides") or {},
        repo_root=SETTINGS.project_root.parent,
    )
    world_overrides = deepcopy(data.get("world_state_overrides") or {})
    safe_overrides = deepcopy(data.get("safe_function_overrides") or {})
    assets = deepcopy(data.get("assets") or {})

    return ThemeConfig(
        id=theme_id,
        label=label,
        description=description,
        version=version,
        prompt_paths=prompt_paths,
        world_overrides=world_overrides,
        safe_function_overrides=safe_overrides,
        assets=assets,
        raw=deepcopy(data),
        source_path=path,
    )


def _normalize_prompt_paths(
    overrides: Dict[str, Any],
    *,
    repo_root: Path,
) -> Dict[str, Path]:
    prompt_paths: Dict[str, Path] = {}
    for key, value in overrides.items():
        key_lower = str(key).strip().lower()
        if not key_lower:
            continue
        resolved = Path(str(value))
        if not resolved.is_absolute():
            resolved = (repo_root / resolved).resolve()
        if not resolved.exists():
            raise ThemeError(f"Prompt override for '{key}' not found: {resolved}")
        prompt_paths[key_lower] = resolved
    return prompt_paths


def _deep_merge(target: Dict[str, Any], overrides: Dict[str, Any]) -> None:
    for key, value in overrides.items():
        if isinstance(value, dict):
            node = target.get(key)
            if isinstance(node, dict):
                _deep_merge(node, value)
            else:
                target[key] = deepcopy(value)
        elif value is None:
            target.pop(key, None)
        else:
            target[key] = deepcopy(value)
