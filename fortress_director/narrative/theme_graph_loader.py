"""Helpers for constructing EventGraph instances from theme files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

from fortress_director.narrative.event_graph import EventGraph, EventNode
from fortress_director.themes.schema import ThemeConfig


def load_event_graph_for_theme(theme: ThemeConfig) -> EventGraph:
    """
    Reads theme.event_graph_file (e.g. JSON/YAML) and builds an EventGraph instance.
    """

    if theme is None:
        raise ValueError("theme config is required")
    graph_path = Path(theme.event_graph_file)
    if not graph_path.is_absolute():
        graph_path = Path(__file__).resolve().parent / graph_path
    payload = _load_graph_payload(graph_path)
    entry_id = payload.get("entry_id")
    if not isinstance(entry_id, str) or not entry_id.strip():
        raise ValueError(f"entry_id missing in event graph file {graph_path}")
    nodes_payload = payload.get("nodes")
    if not isinstance(nodes_payload, list):
        raise ValueError("nodes must be an array of objects")
    nodes: Dict[str, EventNode] = {}
    for entry in nodes_payload:
        if not isinstance(entry, dict):
            raise ValueError("each node entry must be an object")
        node_id = _require_str(entry, "id")
        description = _require_str(entry, "description")
        tags = _coerce_tags(entry.get("tags"))
        next_map = entry.get("next") or {}
        if not isinstance(next_map, dict):
            raise ValueError("node.next must be an object if provided")
        nodes[node_id] = EventNode(
            id=node_id,
            description=description,
            tags=tags,
            next={str(key): str(value) for key, value in next_map.items()},
            is_final=bool(entry.get("is_final", False)),
        )
    return EventGraph(nodes, entry_id=entry_id)


def _load_graph_payload(path: Path) -> Dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        if yaml is None:
            raise
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError("event graph payload must be an object")
    return payload


def _require_str(entry: Dict[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{key} must be non-empty")
    return value


def _coerce_tags(payload: object) -> list[str]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("tags must be an array")
    return [str(tag) for tag in payload]


__all__ = ["load_event_graph_for_theme"]
