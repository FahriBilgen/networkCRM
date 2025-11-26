"""Domain model abstractions for fortress world entities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NPC:
    """Lightweight NPC domain object used by safe functions."""

    id: str
    name: str
    role: str
    x: int
    y: int
    morale: int = 50
    health: int = 100
    fatigue: int = 0
    skills: Dict[str, int] = field(default_factory=dict)
    status_effects: List[str] = field(default_factory=list)
    room: Optional[str] = None
    hostile: bool = False

    def move(self, *, x: int, y: int) -> None:
        self.x = x
        self.y = y


@dataclass
class Structure:
    """Defensive or utility structure in the fortress."""

    id: str
    kind: str
    x: int
    y: int
    integrity: int = 100
    max_integrity: int = 100
    fortification: int = 0
    status: str = "stable"
    on_fire: bool = False

    def reinforce(self, delta: int) -> None:
        self.integrity = max(0, min(self.max_integrity, self.integrity + delta))


@dataclass
class EventMarker:
    """Marker that highlights deterministic events on the tactical map."""

    id: str
    x: int
    y: int
    severity: int
    description: str
    entity_type: str = "marker"


@dataclass
class DomainSnapshot:
    """Convenience container for state + domain translations."""

    npcs: Dict[str, NPC]
    structures: Dict[str, Structure]
    event_markers: Dict[str, EventMarker]

    def npc_positions(self) -> Dict[str, Dict[str, Any]]:
        return {
            npc_id: {
                "x": npc.x,
                "y": npc.y,
                "name": npc.name,
                "role": npc.role,
                "health": npc.health,
                "morale": npc.morale,
                "fatigue": npc.fatigue,
                "hostile": npc.hostile,
            }
            for npc_id, npc in self.npcs.items()
        }

    def structure_integrities(self) -> Dict[str, Dict[str, Any]]:
        return {
            struct_id: {
                "x": struct.x,
                "y": struct.y,
                "kind": struct.kind,
                "integrity": struct.integrity,
                "max_integrity": struct.max_integrity,
                "status": struct.status,
                "on_fire": struct.on_fire,
            }
            for struct_id, struct in self.structures.items()
        }

    def event_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": marker.id,
                "x": marker.x,
                "y": marker.y,
                "severity": marker.severity,
                "description": marker.description,
                "entity_type": marker.entity_type,
                "status": "active",
            }
            for marker in self.event_markers.values()
        ]


def build_domain_snapshot(state: Mapping[str, Any]) -> DomainSnapshot:
    """Map the raw GameState payload to domain dataclasses."""

    npcs = {npc.id: npc for npc in _iter_npcs(state)}
    structures = {struct.id: struct for struct in _iter_structures(state)}
    markers = {marker.id: marker for marker in _iter_event_markers(state)}
    # TODO: retire direct dict access for npc_locations/structures once all callers consume this adapter.
    return DomainSnapshot(npcs=npcs, structures=structures, event_markers=markers)


def sync_npc(state: MutableMapping[str, Any], npc: NPC) -> None:
    """Persist an NPC back into ``state['npc_locations']`` in legacy format."""

    payload = {
        "id": npc.id,
        "name": npc.name,
        "role": npc.role,
        "x": npc.x,
        "y": npc.y,
        "morale": npc.morale,
        "health": npc.health,
        "fatigue": npc.fatigue,
        "skills": dict(npc.skills),
        "status_effects": list(npc.status_effects),
        "room": npc.room,
        "hostile": npc.hostile,
    }
    storage = state.setdefault("npc_locations", [])
    if isinstance(storage, list):
        for idx, entry in enumerate(storage):
            if isinstance(entry, Mapping) and (
                entry.get("id") == npc.id or entry.get("name") == npc.name
            ):
                new_entry = dict(entry)
                new_entry.update(payload)
                storage[idx] = new_entry
                break
        else:
            storage.append(payload)
    elif isinstance(storage, MutableMapping):
        storage[npc.id] = {**storage.get(npc.id, {}), **payload}
    else:
        state["npc_locations"] = [payload]


def sync_structure(state: MutableMapping[str, Any], structure: Structure) -> None:
    """Persist a structure back into ``state['structures']`` in legacy format."""

    payload = {
        "id": structure.id,
        "kind": structure.kind,
        "x": structure.x,
        "y": structure.y,
        "integrity": structure.integrity,
        "max_integrity": structure.max_integrity,
        "fortification": structure.fortification,
        "status": structure.status,
        "on_fire": structure.on_fire,
        # legacy keys kept in sync until callers migrate fully
        "durability": structure.integrity,
        "max_durability": structure.max_integrity,
    }
    storage = state.setdefault("structures", {})
    if isinstance(storage, MutableMapping):
        storage[structure.id] = {**storage.get(structure.id, {}), **payload}
    elif isinstance(storage, list):
        for idx, entry in enumerate(storage):
            if isinstance(entry, Mapping) and entry.get("id") == structure.id:
                new_entry = dict(entry)
                new_entry.update(payload)
                storage[idx] = new_entry
                break
        else:
            storage.append(payload)
    else:
        state["structures"] = {structure.id: payload}


def append_event_marker(state: MutableMapping[str, Any], marker: EventMarker) -> None:
    """Append/replace an event marker entry in ``state['map_event_markers']``."""

    payload = {
        "marker_id": marker.id,
        "bounds": [marker.x, marker.y],
        "severity": marker.severity,
        "description": marker.description,
        "entity_type": marker.entity_type,
    }
    storage = state.setdefault("map_event_markers", [])
    if not isinstance(storage, list):
        state["map_event_markers"] = [payload]
        return
    for idx, entry in enumerate(storage):
        if isinstance(entry, Mapping) and entry.get("marker_id") == marker.id:
            new_entry = dict(entry)
            new_entry.update(payload)
            storage[idx] = new_entry
            break
    else:
        storage.append(payload)


def _iter_npcs(state: Mapping[str, Any]) -> Iterable[NPC]:
    entries = state.get("npc_locations") or []
    if isinstance(entries, Mapping):
        entries = entries.values()
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        npc_id = _coerce_string(entry.get("id") or entry.get("name"))
        if not npc_id:
            continue
        yield NPC(
            id=npc_id,
            name=_coerce_string(entry.get("name")) or npc_id,
            role=_coerce_string(entry.get("role")) or "specialist",
            x=_coerce_int(entry.get("x")),
            y=_coerce_int(entry.get("y")),
            morale=_coerce_int(entry.get("morale"), default=50),
            health=_coerce_int(entry.get("health"), default=100),
            fatigue=_coerce_int(entry.get("fatigue"), default=0),
            skills=_coerce_skill_map(entry.get("skills")),
            status_effects=_coerce_string_list(entry.get("status_effects")),
            room=_coerce_string(entry.get("room")),
            hostile=bool(entry.get("hostile")),
        )


def _iter_structures(state: Mapping[str, Any]) -> Iterable[Structure]:
    entries = state.get("structures")
    iterator: Iterable[Mapping[str, Any]]
    if isinstance(entries, list):
        iterator = entries
    elif isinstance(entries, Mapping):
        iterator = entries.values()
    else:
        iterator = []
    for entry in iterator:
        if not isinstance(entry, Mapping):
            continue
        struct_id = _coerce_string(entry.get("id") or entry.get("name"))
        if not struct_id:
            continue
        max_integrity = _coerce_int(
            entry.get("max_integrity") or entry.get("max_durability") or 100,
            default=100,
        )
        yield Structure(
            id=struct_id,
            kind=_coerce_string(entry.get("kind") or entry.get("type") or "structure"),
            x=_coerce_int(entry.get("x")),
            y=_coerce_int(entry.get("y")),
            integrity=_coerce_int(
                entry.get("integrity") or entry.get("durability") or max_integrity
            ),
            max_integrity=max_integrity,
            fortification=_coerce_int(entry.get("fortification"), default=0),
            status=_coerce_string(entry.get("status")) or "stable",
            on_fire=bool(entry.get("on_fire")),
        )


def _iter_event_markers(state: Mapping[str, Any]) -> Iterable[EventMarker]:
    entries = state.get("map_event_markers") or []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        marker_id = _coerce_string(entry.get("marker_id") or entry.get("id"))
        if not marker_id:
            continue
        x, y = _coerce_pair(entry.get("bounds"))
        yield EventMarker(
            id=marker_id,
            x=x,
            y=y,
            severity=_coerce_int(entry.get("severity"), default=1),
            description=_coerce_string(entry.get("description"))
            or _coerce_string(entry.get("room"))
            or "",
            entity_type=_coerce_string(entry.get("entity_type")) or "marker",
        )


def _coerce_string(value: Any) -> str:
    return str(value) if isinstance(value, str) and value.strip() else ""


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_string_list(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(entry) for entry in value if isinstance(entry, (str, int))]
    return []


def _coerce_skill_map(value: Any) -> Dict[str, int]:
    if isinstance(value, Mapping):
        sanitized: Dict[str, int] = {}
        for key, val in value.items():
            try:
                sanitized[str(key)] = int(val)
            except (TypeError, ValueError):
                continue
        return sanitized
    return {}


def _coerce_pair(value: Any) -> tuple[int, int]:
    if isinstance(value, Mapping):
        return _coerce_int(value.get("x")), _coerce_int(value.get("y"))
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return _coerce_int(value[0]), _coerce_int(value[1])
    return 0, 0
