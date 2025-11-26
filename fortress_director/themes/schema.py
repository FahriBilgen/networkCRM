"""Dataclasses describing the runtime theme configuration schema."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ThemeMapSpec:
    width: int
    height: int
    layout: List[List[str]]  # tile ids, eg. "wall", "gate", "yard"


@dataclass
class ThemeNpcSpec:
    id: str
    name: str
    role: str
    x: int
    y: int
    tags: List[str] = field(default_factory=list)


@dataclass
class ThemeEndingSpec:
    id: str
    label: str
    conditions: Dict[str, Any]  # wall_integrity_min, morale_min vs.


@dataclass
class ThemeConfig:
    id: str
    label: str
    description: str
    map: ThemeMapSpec
    npcs: List[ThemeNpcSpec]
    initial_metrics: Dict[str, Any]
    event_graph_file: str
    safe_function_overrides: Dict[str, Dict[str, Any]]  # name → config (gas, enabled, weights)
    endings: List[ThemeEndingSpec]


__all__ = [
    "ThemeConfig",
    "ThemeEndingSpec",
    "ThemeMapSpec",
    "ThemeNpcSpec",
]
