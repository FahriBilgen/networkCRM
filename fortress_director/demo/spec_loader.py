from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class EndingCondition:
    wall_integrity_min: int
    morale_min: int
    threat_max: int


@dataclass
class DemoSpec:
    id: str
    turn_count: int
    map_width: int
    map_height: int
    initial_state: Dict[str, Any]
    npc_roles: List[str]
    demo_highlights: List[str]
    endings: Dict[str, EndingCondition]


def load_demo_spec(path: str | Path) -> DemoSpec:
    spec_path = Path(path)
    if not spec_path.exists():
        raise FileNotFoundError(spec_path)
    try:
        payload = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - invalid file
        raise ValueError(f"Invalid JSON in {spec_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Demo spec must be a JSON object")

    required_fields = (
        "id",
        "turn_count",
        "map",
        "initial_state",
        "npc_roles",
        "demo_highlights",
        "endings",
    )
    missing = [key for key in required_fields if key not in payload]
    if missing:
        raise ValueError(f"Missing demo spec fields: {', '.join(missing)}")

    map_data = payload.get("map")
    if not isinstance(map_data, dict):
        raise ValueError("map must be an object with width/height")
    try:
        width = int(map_data["width"])
        height = int(map_data["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("map requires integer width/height") from exc

    endings_payload = payload.get("endings")
    ending_conditions: Dict[str, EndingCondition] = {}
    if not isinstance(endings_payload, dict):
        raise ValueError("endings must be an object")
    for ending_id, ending_entry in endings_payload.items():
        if not isinstance(ending_entry, dict):
            raise ValueError(f"Ending '{ending_id}' must be an object")
        conditions = ending_entry.get("conditions")
        if not isinstance(conditions, dict):
            raise ValueError(f"Ending '{ending_id}' missing conditions")
        try:
            ending_conditions[ending_id] = EndingCondition(
                wall_integrity_min=int(conditions["wall_integrity_min"]),
                morale_min=int(conditions["morale_min"]),
                threat_max=int(conditions["threat_max"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Ending '{ending_id}' has invalid condition values"
            ) from exc

    npc_roles = payload.get("npc_roles")
    if not isinstance(npc_roles, list) or not all(
        isinstance(role, str) for role in npc_roles
    ):
        raise ValueError("npc_roles must be a list of strings")

    demo_highlights = payload.get("demo_highlights")
    if not isinstance(demo_highlights, list) or not demo_highlights:
        raise ValueError("demo_highlights must be a non-empty list")

    initial_state = payload.get("initial_state")
    if not isinstance(initial_state, dict):
        raise ValueError("initial_state must be an object")

    return DemoSpec(
        id=str(payload["id"]),
        turn_count=int(payload["turn_count"]),
        map_width=width,
        map_height=height,
        initial_state=initial_state,
        npc_roles=list(npc_roles),
        demo_highlights=list(demo_highlights),
        endings=ending_conditions,
    )
