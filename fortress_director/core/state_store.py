"""Persistent JSON-backed world state store with cold/hot layering."""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from fortress_director.core import domain
from fortress_director.demo.spec_loader import DemoSpec
from fortress_director.settings import (
    ACTIVE_SCHEMA_VERSION,
    DEFAULT_WORLD_STATE,
    SETTINGS,
)
from fortress_director.themes.schema import ThemeConfig
from fortress_director.utils.sqlite_sync import sync_state_to_sqlite
from fortress_director.utils.state_diff import apply_state_diff, compute_state_diff

LOGGER = logging.getLogger(__name__)
DEFAULT_KEY_METRICS = ("order", "morale", "resources", "knowledge", "glitch")
MAX_FOCUS_NPCS = 5
DEFAULT_GRID_SIZE = 12
DEFAULT_MAX_EVENTS = 5
DEFAULT_TURN_LIMIT = int(DEFAULT_WORLD_STATE.get("turn_limit", 30))

DEFAULT_SESSION_STATE: Dict[str, Any] = {
    "turn": 2,
    "turn_limit": DEFAULT_TURN_LIMIT,
    "rng_seed": 12345,
    "last_event_node": None,
    "world": {
        "stability": 58,
        "resources": 82,
        "threat_level": "volatile",
    },
    "metrics": {
        "order": 60,
        "morale": 64,
        "resources": 82,
        "knowledge": 48,
        "glitch": 42,
        "combat": {
            "total_skirmishes": 0,
            "total_casualties_friendly": 0,
            "total_casualties_enemy": 0,
            "last_casualties_friendly": 0,
            "last_casualties_enemy": 0,
        },
    },
    "player_position": {"x": 5, "y": 6},
    "npc_locations": [
        {
            "id": "scout_ila",
            "name": "Scout Ila",
            "x": 3,
            "y": 4,
            "room": "north_wall",
            "hostile": False,
        },
        {
            "id": "engineer_tomas",
            "name": "Engineer Tomas",
            "x": 8,
            "y": 7,
            "room": "workshop",
            "hostile": False,
        },
        {
            "id": "raider_probe",
            "name": "Raider Probe",
            "x": 9,
            "y": 2,
            "room": "east_rampart",
            "hostile": True,
        },
    ],
    # TODO(domain): replace with domain bootstrap helper when downstream UI stops reading raw dicts.
    "structures": {
        "western_wall": {
            "id": "western_wall",
            "kind": "wall",
            "x": 6,
            "y": 1,
            "integrity": 70,
            "max_integrity": 100,
        },
        "inner_gate": {
            "id": "inner_gate",
            "kind": "gate",
            "x": 5,
            "y": 5,
            "integrity": 65,
            "max_integrity": 100,
        },
    },
    "map_event_markers": [
        {
            "marker_id": "supply_cache",
            "bounds": [2, 9],
            "room": "hangar",
            "entity_type": "item",
        },
        {
            "marker_id": "breach_warning",
            "bounds": [10, 3],
            "room": "east_wall",
            "entity_type": "marker",
        },
    ],
    "log": [
        "Scouts repositioned along the eastern gate.",
        "Atmospheric sensors detect incoming stormfront.",
    ],
    "stockpiles": {
        "food": 80,
        "wood": 40,
        "ore": 20,
    },
}
COLD_STATE_KEYS: Set[str] = {
    "recent_events",
    "recent_motifs",
    "recent_world_atmospheres",
    "npc_journal",
    "npc_behavior_timeline",
    "safe_function_history",
    "timeline",
    "room_history",
    "logs",
}
DEFAULT_HISTORY_SUBDIR = "history"
COLD_SNAPSHOT_FILENAME = "cold_latest.json"
DIFF_FILENAME_TEMPLATE = "turn_{turn:04d}.json"


class GameState:
    """In-memory session-bound state container with projection helpers."""

    def __init__(
        self,
        initial_state: Dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> None:
        baseline = deepcopy(initial_state or DEFAULT_SESSION_STATE)
        self._ensure_domain_defaults(baseline)
        self._initial_state = baseline
        self._state = deepcopy(self._initial_state)
        self._domain_cache: domain.DomainSnapshot | None = None
        self._game_over: bool = False
        self._ending_id: str | None = None
        self._last_event_node: str | None = None
        # Track session_id in state for persistence
        self._session_id = session_id
        if session_id:
            self._state["session_id"] = session_id
        self._refresh_game_flow_flags_from_state()

    @classmethod
    def from_demo_spec(
        cls, spec: DemoSpec, session_id: str | None = None
    ) -> "GameState":
        """Construct a deterministic GameState from a DemoSpec."""

        if spec is None:
            raise ValueError("spec is required")
        initial = spec.initial_state
        wall_integrity = int(initial.get("wall_integrity", 0) or 0)
        food = int(initial.get("food", 0) or 0)
        morale = int(initial.get("morale", 0) or 0)
        threat = int(initial.get("threat", 0) or 0)
        npc_locations = cls._build_demo_npcs(spec)
        metrics = {
            "turn": 1,
            "wall_integrity": wall_integrity,
            "food": food,
            "morale": morale,
            "threat": threat,
            "npc_count": int(initial.get("npc_count") or len(npc_locations)),
        }
        state = {
            "turn": 1,
            "turn_limit": int(spec.turn_count),
            "demo_id": spec.id,
            "map": {"width": spec.map_width, "height": spec.map_height},
            "metrics": metrics,
            "_demo_turn_started": False,
            "world": {
                "stability": morale,
                "resources": food,
                "threat_level": "siege",
            },
            "player_position": {
                "x": max(0, min(spec.map_width - 1, spec.map_width // 2)),
                "y": max(0, min(spec.map_height - 1, spec.map_height // 2)),
            },
            "npc_locations": npc_locations,
            "structures": {
                "fortress_wall": {
                    "id": "fortress_wall",
                    "kind": "wall",
                    "x": spec.map_width // 2,
                    "y": 0,
                    "integrity": wall_integrity,
                    "max_integrity": max(100, wall_integrity),
                }
            },
            "map_event_markers": [],
            "log": [
                "Siege demo initialized.",
                "Defenders brace for the 12-turn assault.",
            ],
            "demo_highlights": list(spec.demo_highlights),
            "npc_roles": list(spec.npc_roles),
        }
        if session_id:
            state["session_id"] = session_id
        return cls(state, session_id=session_id)

    @classmethod
    def from_theme_config(
        cls, theme: ThemeConfig, session_id: str | None = None
    ) -> "GameState":
        """Construct GameState state from a ThemeConfig."""

        if theme is None:
            raise ValueError("theme config is required")
        base_state = deepcopy(DEFAULT_SESSION_STATE)
        if session_id:
            base_state["session_id"] = session_id
        base_state["theme_id"] = theme.id
        base_state["theme"] = {
            "id": theme.id,
            "label": theme.label,
            "description": theme.description,
            "event_graph_file": theme.event_graph_file,
            "safe_function_overrides": deepcopy(theme.safe_function_overrides),
            "endings": [
                {
                    "id": ending.id,
                    "label": ending.label,
                    "conditions": deepcopy(ending.conditions),
                }
                for ending in theme.endings
            ],
        }
        base_state["map"] = {
            "width": theme.map.width,
            "height": theme.map.height,
            "layout": deepcopy(theme.map.layout),
        }
        base_state["npc_locations"] = cls._build_theme_npcs(theme)
        player_position = cls._center_player(theme.map.width, theme.map.height)
        player_position["room"] = cls._theme_tile_at(
            theme.map.layout, player_position["x"], player_position["y"]
        )
        base_state["player_position"] = player_position
        base_state["current_room"] = player_position.get("room")
        metrics_override = dict(theme.initial_metrics)
        turn_value = int(metrics_override.pop("turn", base_state.get("turn", 1)) or 1)
        turn_limit_value = metrics_override.pop(
            "turn_limit", base_state.get("turn_limit", DEFAULT_TURN_LIMIT)
        )
        base_state["turn"] = turn_value
        base_state["turn_limit"] = int(turn_limit_value)
        metrics = deepcopy(base_state.get("metrics", {}))
        metrics.update(metrics_override)
        metrics["turn"] = turn_value
        metrics["npc_count"] = len(base_state["npc_locations"])
        base_state["metrics"] = metrics
        world_state = deepcopy(base_state.get("world", {}))
        if "morale" in metrics:
            world_state["stability"] = int(metrics["morale"])
        if "resources" in metrics:
            world_state["resources"] = int(metrics["resources"])
        base_state["world"] = world_state
        base_state["map_event_markers"] = []
        base_state["log"] = ["Theme initialized: " + theme.label]
        return cls(base_state, session_id=session_id)

    def snapshot(self) -> Dict[str, Any]:
        """Return a deep copy of the current state."""

        self._state["game_over"] = self._game_over
        self._state["ending_id"] = self._ending_id
        return deepcopy(self._state)

    def persist(self) -> None:
        """Persist current state to session store (no-op for API sessions without backing store).

        In API mode, GameState is memory-only and relies on SessionManager for in-memory session.
        For file-backed scenarios, this can be overridden. Currently a no-op to allow
        graceful calls from api.py without requiring a backing StateStore.
        """
        # TODO(tier-5): Implement optional file-backed persistence for API sessions
        pass

    def reset(self, state: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Reset to the provided state or the constructor baseline."""

        self._state = deepcopy(state or self._initial_state)
        self._ensure_domain_defaults(self._state)
        self._refresh_game_flow_flags_from_state()
        self._invalidate_domain_cache()
        return self.snapshot()

    def replace(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Overwrite the session state."""

        self._state = deepcopy(state)
        self._ensure_domain_defaults(self._state)
        self._refresh_game_flow_flags_from_state()
        self._invalidate_domain_cache()
        return self.snapshot()

    def apply_delta(self, delta: Dict[str, Any]) -> Dict[str, Any]:
        """Merge *delta* into the session state and return a snapshot."""

        self._state = _gs_merge(self._state, delta)
        self._ensure_domain_defaults(self._state)
        self._refresh_game_flow_flags_from_state()
        self._invalidate_domain_cache()
        return self.snapshot()

    def get_projected_state(
        self,
        full_state: Dict[str, Any] | None = None,
        *,
        grid_size: int = DEFAULT_GRID_SIZE,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> Dict[str, Any]:
        """Return an LLM-friendly projection of the current state."""

        source = full_state or self._state
        return _gs_build_projection(source, grid_size, max_events)

    def as_domain(self) -> domain.DomainSnapshot:
        """Return a cached DomainSnapshot for the current state."""

        if self._domain_cache is None:
            self._domain_cache = domain.build_domain_snapshot(self._state)
        return self._domain_cache

    def get_npc(self, npc_id: str) -> domain.NPC | None:
        """Return an NPC if present in the state."""

        if not npc_id:
            return None
        return self.as_domain().npcs.get(str(npc_id))

    def get_npc_by_id(self, npc_id: str) -> domain.NPC | None:
        """Return an NPC if present in the state."""

        return self.get_npc(npc_id)

    def get_npcs_in_area(self, x1: int, y1: int, x2: int, y2: int) -> List[domain.NPC]:
        """Return all NPCs inside the inclusive rectangle."""

        min_x, max_x = sorted((int(x1), int(x2)))
        min_y, max_y = sorted((int(y1), int(y2)))
        return [
            npc
            for npc in self.as_domain().npcs.values()
            if min_x <= npc.x <= max_x and min_y <= npc.y <= max_y
        ]

    def get_structure(self, structure_id: str) -> domain.Structure | None:
        """Return a structure if it exists."""

        if not structure_id:
            return None
        return self.as_domain().structures.get(str(structure_id))

    def move_npc(
        self, npc_id: str, x: int, y: int, *, room: str | None = None
    ) -> domain.NPC:
        """Move an NPC to absolute coordinates and optionally update room."""

        npc = self.get_npc(npc_id)
        if npc is None:
            raise KeyError(f"NPC '{npc_id}' not found")
        npc.move(x=max(0, int(x)), y=max(0, int(y)))
        if room:
            npc.room = room
        domain.sync_npc(self._state, npc)
        self._invalidate_domain_cache()
        return npc

    def update_npc(self, npc_id: str, **updates: Any) -> domain.NPC:
        """Apply attribute updates to an NPC and persist to state."""

        npc = self.get_npc(npc_id)
        if npc is None:
            raise KeyError(f"NPC '{npc_id}' not found")
        for field_name, value in updates.items():
            if hasattr(npc, field_name):
                setattr(npc, field_name, value)
        domain.sync_npc(self._state, npc)
        self._invalidate_domain_cache()
        return npc

    def update_structure(self, structure_id: str, **updates: Any) -> domain.Structure:
        """Apply attribute updates to a structure."""

        struct = self.get_structure(structure_id)
        if struct is None:
            raise KeyError(f"Structure '{structure_id}' not found")
        for field_name, value in updates.items():
            if hasattr(struct, field_name):
                setattr(struct, field_name, value)
        domain.sync_structure(self._state, struct)
        self._invalidate_domain_cache()
        return struct

    def remove_event_marker(self, marker_id: str) -> bool:
        """Remove an event marker by id."""

        storage = self._state.get("map_event_markers")
        if not isinstance(storage, list):
            return False
        initial_len = len(storage)
        updated = [
            marker
            for marker in storage
            if not (
                isinstance(marker, dict)
                and str(marker.get("marker_id") or marker.get("id")) == marker_id
            )
        ]
        self._state["map_event_markers"] = updated
        changed = len(updated) < initial_len
        if changed:
            self._invalidate_domain_cache()
        return changed

    def add_log_entry(self, message: str) -> None:
        """Append a deterministic message to the session log."""

        log = self._state.setdefault("log", [])
        if isinstance(log, list):
            log.append(str(message))

    def set_flag(self, flag: str) -> None:
        """Ensure the provided gameplay flag is enabled."""

        flags = self._state.setdefault("flags", [])
        if isinstance(flags, list) and flag not in flags:
            flags.append(flag)

    def clear_flag(self, flag: str) -> None:
        """Remove a gameplay flag if present."""

        flags = self._state.get("flags")
        if isinstance(flags, list):
            self._state["flags"] = [entry for entry in flags if entry != flag]

    def add_state_tag(self, tag: str) -> None:
        """Attach a simple tag to the state for downstream consumers."""

        tags = self._state.setdefault("state_tags", [])
        if isinstance(tags, list) and tag not in tags:
            tags.append(tag)

    def adjust_npc_focus_level(self, npc_id: str, delta: int) -> int:
        """Adjust focus tracking for an NPC and return the new value."""

        storage = self._state.setdefault("npc_focus_levels", {})
        if not isinstance(storage, dict):
            storage = {}
            self._state["npc_focus_levels"] = storage
        current = int(storage.get(npc_id, 0) or 0)
        new_value = max(0, current + int(delta))
        storage[npc_id] = new_value
        return new_value

    def grant_npc_equipment(self, npc_id: str, item: str) -> List[str]:
        """Record equipment assigned to an NPC."""

        storage = self._state.setdefault("npc_equipment", {})
        if not isinstance(storage, dict):
            storage = {}
            self._state["npc_equipment"] = storage
        items = storage.setdefault(npc_id, [])
        if isinstance(items, list) and item not in items:
            items.append(item)
        return list(items)

    def set_npc_patrol(self, npc_id: str, duration: int) -> None:
        """Mark an NPC as deployed on patrol."""

        storage = self._state.setdefault("npc_patrols", {})
        if not isinstance(storage, dict):
            storage = {}
            self._state["npc_patrols"] = storage
        storage[npc_id] = {"remaining": max(0, int(duration))}

    def clear_npc_patrol(self, npc_id: str) -> None:
        """Clear patrol tracking for an NPC."""

        storage = self._state.get("npc_patrols")
        if isinstance(storage, dict) and npc_id in storage:
            storage.pop(npc_id, None)

    def adjust_structure_integrity(
        self,
        structure_id: str,
        delta: int,
        *,
        kind: str | None = None,
    ) -> domain.Structure:
        """Adjust integrity for the requested structure."""

        structure = self.as_domain().structures.get(structure_id)
        if structure is None:
            structure = domain.Structure(
                id=structure_id,
                kind=kind or "structure",
                x=0,
                y=0,
                integrity=0,
            )
        elif kind:
            structure.kind = kind
        structure.reinforce(int(delta))
        domain.sync_structure(self._state, structure)
        self._invalidate_domain_cache()
        return structure

    def add_event_marker(
        self,
        *,
        marker_id: str | None = None,
        x: int,
        y: int,
        severity: int = 1,
        description: str = "",
        entity_type: str = "event",
    ) -> domain.EventMarker:
        """Add a deterministic event marker to the tactical map."""

        marker = domain.EventMarker(
            id=marker_id or self._next_marker_id(),
            x=max(0, int(x)),
            y=max(0, int(y)),
            severity=max(1, int(severity)),
            description=description,
            entity_type=entity_type,
        )
        domain.append_event_marker(self._state, marker)
        self._invalidate_domain_cache()
        return marker

    def adjust_metric(self, metric: str, delta: int) -> int:
        """Adjust a numeric metric and return the new value."""

        metrics = self._state.setdefault("metrics", {})
        before = int(metrics.get(metric, 0) or 0)
        metrics[metric] = before + int(delta)
        return metrics[metric]

    def adjust_world_stat(self, stat: str, delta: int) -> int:
        """Adjust a top-level world stat such as stability or resources."""

        world = self._state.setdefault("world", {})
        before = int(world.get(stat, 0) or 0)
        world[stat] = before + int(delta)
        return world[stat]

    def record_combat_metrics(
        self,
        *,
        friendly_casualties: int,
        enemy_casualties: int,
    ) -> Dict[str, int]:
        """Update combat metric counters and return the updated payload."""

        metrics = self._state.setdefault("metrics", {})
        combat = metrics.setdefault("combat", {})
        total_skirmishes = int(combat.get("total_skirmishes", 0) or 0) + 1
        friendly_total = int(combat.get("total_casualties_friendly", 0) or 0) + max(
            0, int(friendly_casualties)
        )
        enemy_total = int(combat.get("total_casualties_enemy", 0) or 0) + max(
            0, int(enemy_casualties)
        )
        combat.update(
            {
                "total_skirmishes": total_skirmishes,
                "total_casualties_friendly": friendly_total,
                "total_casualties_enemy": enemy_total,
                "last_casualties_friendly": max(0, int(friendly_casualties)),
                "last_casualties_enemy": max(0, int(enemy_casualties)),
            }
        )
        return dict(combat)

    @staticmethod
    def _build_theme_npcs(theme: ThemeConfig) -> List[Dict[str, Any]]:
        layout = theme.map.layout
        npcs: List[Dict[str, Any]] = []
        for spec in theme.npcs:
            room = GameState._theme_tile_at(layout, spec.x, spec.y)
            npcs.append(
                {
                    "id": spec.id,
                    "name": spec.name,
                    "role": spec.role,
                    "x": spec.x,
                    "y": spec.y,
                    "room": room,
                    "hostile": False,
                    "tags": list(spec.tags),
                }
            )
        return npcs

    @staticmethod
    def _center_player(width: int, height: int) -> Dict[str, int]:
        width = max(1, int(width))
        height = max(1, int(height))
        x = max(0, min(width - 1, width // 2))
        y = max(0, min(height - 1, height // 2))
        return {"x": x, "y": y}

    @staticmethod
    def _theme_tile_at(layout: List[List[str]], x: int, y: int) -> str | None:
        if not layout:
            return None
        if y < 0 or y >= len(layout):
            return None
        row = layout[y]
        if not isinstance(row, list):
            return None
        if x < 0 or x >= len(row):
            return None
        cell = row[x]
        return str(cell) if cell is not None else None

    @staticmethod
    def _build_demo_npcs(spec: DemoSpec) -> List[Dict[str, Any]]:
        width = max(1, spec.map_width)
        height = max(1, spec.map_height)
        wall_slots = [
            (1, 1, "outer_wall"),
            (max(1, width // 4), 1, "outer_wall"),
            (max(1, width // 2), 1, "outer_wall"),
            (max(1, width - 2), 2, "outer_wall"),
        ]
        courtyard_slots = [
            (max(1, width // 3), max(1, height // 2), "courtyard"),
            (max(1, (2 * width) // 3), max(1, height // 2), "courtyard"),
            (max(1, width // 2), max(1, (height // 2) + 1), "courtyard"),
            (max(1, width // 2), max(1, height - 2), "courtyard"),
        ]
        slots = wall_slots + courtyard_slots
        if not slots:
            slots = [(width // 2, height // 2, "courtyard")]
        npcs: List[Dict[str, Any]] = []
        for idx, role in enumerate(spec.npc_roles):
            slot_x, slot_y, room = slots[idx % len(slots)]
            x = max(0, min(width - 1, slot_x))
            y = max(0, min(height - 1, slot_y))
            display_role = role.replace("_", " ").title()
            npcs.append(
                {
                    "id": f"npc_{idx + 1}",
                    "name": f"{display_role} {idx + 1}",
                    "role": role,
                    "x": x,
                    "y": y,
                    "room": room,
                    "hostile": False,
                }
            )
        return npcs

    @staticmethod
    def compute_state_delta(
        old_state: Dict[str, Any] | None,
        new_state: Dict[str, Any],
        *,
        max_events: int = 3,
    ) -> Dict[str, Any]:
        """Produce a compact delta summary between two snapshots."""

        return _gs_state_delta(old_state, new_state, max_events=max_events)

    def _next_marker_id(self) -> str:
        counter = int(self._state.get("_event_marker_seq", 0) or 0) + 1
        self._state["_event_marker_seq"] = counter
        return f"event_{counter:03d}"

    def _invalidate_domain_cache(self) -> None:
        self._domain_cache = None

    def _refresh_game_flow_flags_from_state(self) -> None:
        ending_value = self._state.get("ending_id")
        self._ending_id = str(ending_value) if ending_value is not None else None
        self._game_over = bool(self._state.get("game_over", False))
        last_node_value = self._state.get("last_event_node")
        self._last_event_node = str(last_node_value) if last_node_value else None
        self._state["game_over"] = self._game_over
        self._state["ending_id"] = self._ending_id
        self._state["last_event_node"] = self._last_event_node

    @property
    def turn(self) -> int:
        metrics = self._state.get("metrics") or {}
        raw_turn = metrics.get("turn", self._state.get("turn", 0))
        try:
            return int(raw_turn)
        except (TypeError, ValueError):
            return 0

    @turn.setter
    def turn(self, value: int) -> None:
        metrics = self._state.setdefault("metrics", {})
        coerced = max(0, int(value))
        metrics["turn"] = coerced
        self._state["turn"] = coerced

    @property
    def turn_limit(self) -> int:
        value = self._state.get("turn_limit", DEFAULT_TURN_LIMIT)
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            self._state["turn_limit"] = DEFAULT_TURN_LIMIT
            return DEFAULT_TURN_LIMIT

    @turn_limit.setter
    def turn_limit(self, value: int) -> None:
        self._state["turn_limit"] = max(1, int(value))

    @property
    def rng_seed(self) -> int:
        value = self._state.setdefault("rng_seed", 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            self._state["rng_seed"] = 0
            return 0

    @rng_seed.setter
    def rng_seed(self, value: int) -> None:
        self._state["rng_seed"] = int(value)

    @property
    def game_over(self) -> bool:
        return self._game_over

    @game_over.setter
    def game_over(self, value: bool) -> None:
        self._game_over = bool(value)
        self._state["game_over"] = self._game_over

    @property
    def ending_id(self) -> str | None:
        return self._ending_id

    @ending_id.setter
    def ending_id(self, value: str | None) -> None:
        self._ending_id = None if value is None else str(value)
        self._state["ending_id"] = self._ending_id

    @property
    def last_event_node(self) -> str | None:
        return self._last_event_node

    @last_event_node.setter
    def last_event_node(self, value: str | None) -> None:
        self._last_event_node = None if not value else str(value)
        self._state["last_event_node"] = self._last_event_node

    @staticmethod
    def _ensure_domain_defaults(state: Dict[str, Any]) -> None:
        state.setdefault("npc_locations", [])
        state.setdefault("structures", {})
        state.setdefault("map_event_markers", [])
        state.setdefault("flags", [])
        state.setdefault("state_tags", [])
        state.setdefault("npc_focus_levels", {})
        state.setdefault("npc_equipment", {})
        state.setdefault("npc_patrols", {})
        state.setdefault("game_over", False)
        metrics = state.setdefault("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
            state["metrics"] = metrics
        combat_metrics = metrics.setdefault("combat", {})
        if not isinstance(combat_metrics, dict):
            combat_metrics = {}
            metrics["combat"] = combat_metrics
        combat_metrics.setdefault("total_skirmishes", 0)
        combat_metrics.setdefault("total_casualties_friendly", 0)
        combat_metrics.setdefault("total_casualties_enemy", 0)
        combat_metrics.setdefault("last_casualties_friendly", 0)
        combat_metrics.setdefault("last_casualties_enemy", 0)
        stockpiles = state.setdefault("stockpiles", {"food": 0, "wood": 0, "ore": 0})
        if not isinstance(stockpiles, dict):
            stockpiles = {"food": 0, "wood": 0, "ore": 0}
            state["stockpiles"] = stockpiles
        stockpiles.setdefault("food", 0)
        stockpiles.setdefault("wood", 0)
        stockpiles.setdefault("ore", 0)
        if "ending_id" not in state:
            state["ending_id"] = None
        if "last_event_node" not in state:
            state["last_event_node"] = None
        state.setdefault("turn_limit", DEFAULT_TURN_LIMIT)
        state.setdefault("rng_seed", 0)


class StateStore:
    """Lightweight JSON-backed state store."""

    def __init__(self, path: Path, db_path: Path | None = None) -> None:
        self._path = path
        if db_path is not None:
            self._db_path = Path(db_path)
        elif path == SETTINGS.world_state_path:
            self._db_path = SETTINGS.db_path
        else:
            self._db_path = path.with_suffix(".sqlite")
        self._history_dir = self._path.parent / DEFAULT_HISTORY_SUBDIR
        self._cold_cache: Dict[str, Any] = {}
        self._state = self._load()
        self.glitch_manager = None

    def snapshot(self) -> Dict[str, Any]:
        """Return a deep copy of the current state for safe mutation."""

        snapshot = deepcopy(self._state)
        LOGGER.debug(
            "State snapshot loaded from %s (turn=%s)",
            self._path,
            snapshot.get("turn"),
        )
        return snapshot

    def test_method(self):
        """Test method to check if class parsing works."""
        return {"test": True}

    def persist(self, state: Dict[str, Any]) -> None:
        """Replace current state with provided snapshot and flush to disk."""

        self._state = deepcopy(state)
        sync_state_to_sqlite(self._state, db_path=self._db_path)
        cold_meta = self._write_cold_layers(self._state)
        payload = json.dumps(
            self._build_hot_payload(self._state, cold_meta),
            indent=2,
        )
        self._path.write_text(payload, encoding="utf-8")
        LOGGER.debug(
            "State persisted to %s (turn=%s)",
            self._path,
            state.get("turn"),
        )

    def _load(self) -> Dict[str, Any]:
        if not self._path.exists():
            return self._fresh_default()
        text = self._path.read_text(encoding="utf-8").strip()
        if not text:
            LOGGER.debug(
                "World state file %s empty; loading defaults",
                self._path,
            )
            return self._fresh_default()
        try:
            payload = json.loads(text) or {}
        except json.JSONDecodeError:
            LOGGER.warning(
                "World state file %s corrupt; loading defaults",
                self._path,
            )
            return self._fresh_default()
        if not isinstance(payload, dict):  # pragma: no cover - defensive guard
            return self._fresh_default()

        cold_state = self._hydrate_cold_state(payload)
        merged = self._merge_with_defaults(payload)
        for key, value in cold_state.items():
            merged[key] = value
        merged.pop("_cold_refs", None)
        merged = self._apply_schema_migrations(merged)
        self._cold_cache = self._extract_cold_state(merged)
        return merged

    @staticmethod
    def _fresh_default() -> Dict[str, Any]:
        return deepcopy(DEFAULT_WORLD_STATE)

    @classmethod
    def _merge_with_defaults(cls, overrides: Dict[str, Any]) -> Dict[str, Any]:
        base = deepcopy(DEFAULT_WORLD_STATE)
        return cls._deep_merge(base, overrides)

    @staticmethod
    def _apply_schema_migrations(state: Dict[str, Any]) -> Dict[str, Any]:
        version = int(state.get("schema_version", 1) or 1)
        if version < 2:
            state.setdefault("environment_hazards", [])
            state.setdefault(
                "weather_pattern",
                {"pattern": "overcast", "remaining": 0, "lock_until": 0},
            )
            state.setdefault("structures", {})
            state.setdefault("npc_schedule", {})
            state.setdefault("patrols", {})
            state.setdefault("combat_log", [])
            state.setdefault("item_transfers", [])
            state.setdefault("stockpiles", {"food": 0, "wood": 0, "ore": 0})
            state.setdefault("stockpile_log", [])
            state.setdefault("trade_routes", {})
            state.setdefault("trade_route_history", [])
            state.setdefault("scheduled_events", [])
            state.setdefault(
                "story_progress",
                {"act": "build_up", "progress": 0.0, "act_history": []},
            )
            state.setdefault("timeline", [])
            state.setdefault("hazard_cooldowns", {})
            state.setdefault("schema_notes", {})
            state.setdefault("locked_options", {})
            state.setdefault("recent_world_atmospheres", [])
            state.setdefault("last_weather_change_turn", None)
            state["schema_version"] = ACTIVE_SCHEMA_VERSION
        else:
            state["schema_version"] = max(version, ACTIVE_SCHEMA_VERSION)
        return state

    @staticmethod
    def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = StateStore._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def _history_directory(self) -> Path:
        return self._history_dir

    def _resolve_history_path(self, history_dir: Optional[str]) -> Path:
        if not history_dir:
            return self._history_directory()
        candidate = Path(history_dir)
        if not candidate.is_absolute():
            candidate = (self._path.parent / candidate).resolve()
        return candidate

    def _hydrate_cold_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        refs = payload.get("_cold_refs")
        if not isinstance(refs, dict):
            return {}
        history_dir = self._resolve_history_path(refs.get("history_dir"))
        snapshot_name = refs.get("snapshot", COLD_SNAPSHOT_FILENAME)
        snapshot_path = history_dir / snapshot_name
        cold_state: Dict[str, Any] = {}
        snapshot_turn: Optional[int] = None
        if snapshot_path.exists():
            try:
                snapshot_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                snapshot_payload = {}
            if isinstance(snapshot_payload, dict) and "state" in snapshot_payload:
                cold_state = snapshot_payload.get("state") or {}
                snapshot_turn = snapshot_payload.get("turn")
            elif isinstance(snapshot_payload, dict):
                cold_state = snapshot_payload
        latest_turn = refs.get("latest_turn")
        try:
            latest_turn = int(latest_turn) if latest_turn is not None else None
        except (TypeError, ValueError):
            latest_turn = None
        start_turn = snapshot_turn if isinstance(snapshot_turn, int) else None
        if latest_turn is not None and (start_turn is None or latest_turn > start_turn):
            apply_from = (start_turn or 0) + 1
            for turn in range(apply_from, latest_turn + 1):
                diff_path = history_dir / DIFF_FILENAME_TEMPLATE.format(turn=turn)
                if not diff_path.exists():
                    continue
                try:
                    diff_payload = json.loads(diff_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                entries = (
                    diff_payload.get("diff") if isinstance(diff_payload, dict) else None
                )
                if isinstance(entries, list):
                    apply_state_diff(cold_state, entries)
        payload.pop("_cold_refs", None)
        return cold_state

    def _extract_cold_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cold: Dict[str, Any] = {}
        for key in COLD_STATE_KEYS:
            if key in state:
                cold[key] = deepcopy(state[key])
        return cold

    def _write_cold_layers(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cold_state = self._extract_cold_state(state)
        if not cold_state:
            self._cold_cache = {}
            return None
        history_dir = self._history_directory()
        history_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = history_dir / COLD_SNAPSHOT_FILENAME
        turn_value = int(state.get("turn") or state.get("current_turn") or 0)
        snapshot_payload = {"turn": turn_value, "state": cold_state}
        snapshot_path.write_text(
            json.dumps(snapshot_payload, indent=2), encoding="utf-8"
        )
        previous = self._cold_cache or {}
        diff_entries = compute_state_diff(previous, cold_state)
        if diff_entries:
            diff_path = history_dir / DIFF_FILENAME_TEMPLATE.format(turn=turn_value)
            diff_payload = {"turn": turn_value, "diff": diff_entries}
            diff_path.write_text(json.dumps(diff_payload, indent=2), encoding="utf-8")
        self._cold_cache = deepcopy(cold_state)
        rel_history = os.path.relpath(history_dir, self._path.parent)
        meta: Dict[str, Any] = {
            "history_dir": rel_history,
            "latest_turn": turn_value,
            "snapshot": COLD_SNAPSHOT_FILENAME,
        }
        if diff_entries:
            meta["latest_diff"] = DIFF_FILENAME_TEMPLATE.format(turn=turn_value)
        return meta

    def _build_hot_payload(
        self,
        state: Dict[str, Any],
        cold_meta: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        hot_state = deepcopy(state)
        for key in COLD_STATE_KEYS:
            hot_state.pop(key, None)
        if cold_meta:
            hot_state["_cold_refs"] = cold_meta
        else:
            hot_state.pop("_cold_refs", None)
        return hot_state

    def summary(self) -> Dict[str, Any]:
        """Provide a user-facing snapshot for CLI debug output."""

        state = self._state
        return {
            "turn": state.get("turn"),
            "day": state.get("day"),
            "time": state.get("time"),
            "current_room": state.get("current_room"),
            "recent_events": state.get("recent_events", [])[-3:],
            "recent_motifs": state.get("recent_motifs", [])[-3:],
        }


def _gs_build_projection(
    source: Dict[str, Any], grid_size: int, max_events: int
) -> Dict[str, Any]:
    projected: Dict[str, Any] = {
        "turn": _gs_coerce_int(source.get("turn")),
        "world": deepcopy(source.get("world", {})),
        "metrics": _gs_select_metrics(source),
        "nearby_grid": _gs_build_nearby_grid(source, grid_size),
        "npc_focus": _gs_select_npc_focus(source),
        "recent_events": _gs_gather_recent_events(source, max_events),
    }
    flags = source.get("flags")
    if isinstance(flags, list) and flags:
        projected["flags"] = list(flags[:8])
    return projected


def _gs_state_delta(
    old_state: Dict[str, Any] | None,
    new_state: Dict[str, Any],
    *,
    max_events: int,
) -> Dict[str, Any]:
    previous = old_state or {}
    delta: Dict[str, Any] = {}
    metrics_delta: Dict[str, int] = {}
    prev_metrics = previous.get("metrics", {})
    next_metrics = new_state.get("metrics", {})
    for key in DEFAULT_KEY_METRICS:
        before = _gs_coerce_int(prev_metrics.get(key))
        after = _gs_coerce_int(next_metrics.get(key))
        if after != before:
            metrics_delta[key] = after - before
    if metrics_delta:
        delta["metrics"] = metrics_delta

    old_flags = set(_gs_coerce_flag_list(previous.get("flags")))
    new_flags = set(_gs_coerce_flag_list(new_state.get("flags")))
    added = sorted(new_flags - old_flags)
    removed = sorted(old_flags - new_flags)
    if added:
        delta["flags_added"] = added
    if removed:
        delta["flags_removed"] = removed

    recent_old = set(_gs_gather_recent_events(previous, max_events))
    recent_new = _gs_gather_recent_events(new_state, max_events)
    recent_diff = [entry for entry in recent_new if entry not in recent_old]
    if recent_diff:
        delta["recent_events"] = recent_diff
    return delta


def _gs_merge(base: Any, delta: Any) -> Any:
    if isinstance(base, dict) and isinstance(delta, dict):
        merged = {key: deepcopy(value) for key, value in base.items()}
        for key, value in delta.items():
            if key in merged:
                merged[key] = _gs_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
    if isinstance(base, list) and isinstance(delta, list):
        merged_list = deepcopy(base)
        merged_list.extend(deepcopy(delta))
        return merged_list
    if isinstance(base, (int, float)) and isinstance(delta, (int, float)):
        return base + delta
    return deepcopy(delta)


def _gs_select_metrics(state: Dict[str, Any]) -> Dict[str, int]:
    metrics = state.get("metrics") or {}
    selected: Dict[str, int] = {}
    for key in DEFAULT_KEY_METRICS:
        selected[key] = _gs_coerce_int(metrics.get(key))
    return selected


def _gs_build_nearby_grid(
    state: Dict[str, Any], grid_size: int
) -> List[Dict[str, Any]]:
    grid: List[Dict[str, Any]] = []
    player = state.get("player_position") or {"x": grid_size // 2, "y": grid_size // 2}
    player_point = _gs_coerce_point(player, grid_size)
    if player_point:
        grid.append(
            {
                "id": "player",
                "x": player_point["x"],
                "y": player_point["y"],
                "room": state.get("current_room"),
                "hostile": False,
                "entity_type": "player",
            },
        )
    for npc in _gs_iterate_npc_locations(state):
        coords = _gs_coerce_point(npc, grid_size)
        if not coords:
            continue
        grid.append(
            {
                "id": npc.get("id") or npc.get("name"),
                "x": coords["x"],
                "y": coords["y"],
                "room": npc.get("room"),
                "hostile": bool(npc.get("hostile")),
                "entity_type": "npc_hostile" if npc.get("hostile") else "npc",
            },
        )
    for marker in state.get("map_event_markers", []):
        coords = _gs_coerce_point(marker.get("bounds"), grid_size)
        if not coords:
            continue
        grid.append(
            {
                "id": marker.get("marker_id"),
                "x": coords["x"],
                "y": coords["y"],
                "room": marker.get("room"),
                "hostile": False,
                "entity_type": marker.get("entity_type") or "marker",
            },
        )
    return grid[: grid_size * 2]


def _gs_iterate_npc_locations(state: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    locations = state.get("npc_locations")
    if isinstance(locations, dict):
        for entry in locations.values():
            if isinstance(entry, dict):
                yield entry
    elif isinstance(locations, list):
        for entry in locations:
            if isinstance(entry, dict):
                yield entry


def _gs_coerce_point(payload: Any, grid_size: int) -> Optional[Dict[str, int]]:
    if isinstance(payload, dict):
        x = payload.get("x")
        y = payload.get("y")
    elif isinstance(payload, (list, tuple)) and len(payload) >= 2:
        x, y = payload[0], payload[1]
    else:
        return None
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    x_i = max(0, min(grid_size - 1, int(x)))
    y_i = max(0, min(grid_size - 1, int(y)))
    return {"x": x_i, "y": y_i}


def _gs_select_npc_focus(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    focus: List[Dict[str, Any]] = []
    player_room = state.get("current_room")
    important_flags = set(_gs_coerce_flag_list(state.get("flags")))
    for npc in state.get("npc_locations", []):
        if not isinstance(npc, dict):
            continue
        npc_flags = set(_gs_coerce_flag_list(npc.get("flags")))
        prioritized = (
            npc.get("room") == player_room
            or bool(npc.get("hostile"))
            or bool(npc_flags & important_flags)
        )
        if prioritized:
            focus.append(
                {
                    "id": npc.get("id") or npc.get("name"),
                    "name": npc.get("name"),
                    "room": npc.get("room"),
                    "role": npc.get("role"),
                    "stance": npc.get("stance"),
                    "hostile": bool(npc.get("hostile")),
                },
            )
    if not focus:
        for npc in state.get("npc_locations", [])[:MAX_FOCUS_NPCS]:
            if isinstance(npc, dict):
                focus.append(
                    {
                        "id": npc.get("id") or npc.get("name"),
                        "name": npc.get("name"),
                        "room": npc.get("room"),
                        "role": npc.get("role"),
                        "stance": npc.get("stance"),
                        "hostile": bool(npc.get("hostile")),
                    },
                )
    return focus[:MAX_FOCUS_NPCS]


def _gs_gather_recent_events(state: Dict[str, Any], limit: int) -> List[str]:
    entries: List[Any] = []
    for key in ("recent_events", "log", "logs"):
        values = state.get(key)
        if isinstance(values, list):
            entries.extend(values)
    combat_log = state.get("combat_log")
    if isinstance(combat_log, list):
        entries.extend(combat_log)
    choices = state.get("player_choice_history")
    if isinstance(choices, list):
        for choice in choices:
            if isinstance(choice, dict):
                entries.append(choice.get("text"))
    if not entries:
        return []
    serialized = [_gs_stringify_event(entry) for entry in entries if entry]
    return serialized[-limit:]


def _gs_stringify_event(entry: Any) -> str:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        for key in ("summary", "text", "description", "name"):
            if entry.get(key):
                return str(entry[key])
    return str(entry)


def _gs_coerce_flag_list(flags: Any) -> List[str]:
    if flags is None:
        return []
    if isinstance(flags, list):
        iterable: Iterable[Any] = flags
    else:
        iterable = [flags]
    result: List[str] = []
    for value in iterable:
        if value is None:
            continue
        result.append(str(value).lower())
    return result


def _gs_coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
