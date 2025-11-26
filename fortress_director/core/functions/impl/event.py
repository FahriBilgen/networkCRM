from __future__ import annotations

from typing import Any, Dict

from fortress_director.core.function_registry import bind_handler, load_defaults
from fortress_director.core.state_store import GameState

load_defaults()


def _response(
    log: str,
    *,
    status: str = "applied",
    metrics: Dict[str, int] | None = None,
    effects: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "log": log,
        "metrics": metrics or {},
        "effects": effects or {},
    }


def spawn_event_marker_handler(
    game_state: GameState,
    marker_id: str,
    x: int,
    y: int,
    severity: int | None = None,
) -> Dict[str, Any]:
    marker = game_state.add_event_marker(
        marker_id=marker_id,
        x=int(x),
        y=int(y),
        severity=max(1, int(severity or 1)),
        description=f"Event at ({x}, {y})",
        entity_type="event",
    )
    log = f"Marker {marker.id} placed at ({marker.x}, {marker.y})."
    return _response(
        log,
        effects={"marker_id": marker.id, "position": {"x": marker.x, "y": marker.y}},
    )


def remove_event_marker_handler(game_state: GameState, marker_id: str) -> Dict[str, Any]:
    removed = game_state.remove_event_marker(marker_id)
    log = f"Marker {marker_id} removed." if removed else f"Marker {marker_id} not found."
    return _response(log, status="applied" if removed else "noop")


def trigger_alarm_handler(
    game_state: GameState, level: str, message: str | None = None
) -> Dict[str, Any]:
    game_state.set_flag(f"alarm_{level}")
    log = message or f"Alarm raised to {level}."
    return _response(log, effects={"level": level})


def create_storm_handler(
    game_state: GameState, duration: int, intensity: int
) -> Dict[str, Any]:
    game_state.set_flag("storm_active")
    morale_hit = -max(1, int(intensity) // 2)
    game_state.adjust_metric("morale", morale_hit)
    log = f"Storm created for {duration} turns."
    return _response(log, metrics={"morale": morale_hit})


def extinguish_storm_handler(game_state: GameState, duration: int) -> Dict[str, Any]:
    game_state.clear_flag("storm_active")
    morale = game_state.adjust_metric("morale", max(1, int(duration) // 2))
    log = "Storm dissipated."
    return _response(log, effects={"morale": morale})


def collapse_tunnel_handler(game_state: GameState, tunnel_id: str) -> Dict[str, Any]:
    game_state.set_flag(f"tunnel_collapsed_{tunnel_id}")
    log = f"Tunnel {tunnel_id} collapsed."
    return _response(log, effects={"tunnel_id": tunnel_id})


def reinforce_tunnel_handler(
    game_state: GameState, tunnel_id: str, amount: int
) -> Dict[str, Any]:
    struct = game_state.adjust_structure_integrity(tunnel_id, int(amount), kind="tunnel")
    log = f"Tunnel {tunnel_id} reinforced."
    return _response(
        log,
        effects={"tunnel_id": tunnel_id, "integrity": struct.integrity},
    )


def flood_area_handler(game_state: GameState, zone: str, severity: int) -> Dict[str, Any]:
    marker = game_state.add_event_marker(
        marker_id=f"flood_{zone}",
        x=0,
        y=0,
        severity=max(1, int(severity)),
        description=f"Flooding in {zone}",
        entity_type="flood",
    )
    log = f"{zone} flooded to slow attackers."
    return _response(log, effects={"marker_id": marker.id})


def create_signal_fire_handler(
    game_state: GameState, location: str, intensity: int
) -> Dict[str, Any]:
    marker = game_state.add_event_marker(
        marker_id=f"signal_{location}",
        x=0,
        y=0,
        severity=max(1, int(intensity)),
        description=f"Signal fire lit at {location}",
        entity_type="signal",
    )
    log = f"Signal fire ignited at {location}."
    return _response(log, effects={"marker_id": marker.id})


def set_watch_lights_handler(
    game_state: GameState, section: str, brightness: int
) -> Dict[str, Any]:
    game_state.set_flag(f"lights_{section}")
    log = f"Watch lights set along {section} (brightness {brightness})."
    return _response(log, effects={"section": section, "brightness": brightness})


bind_handler("spawn_event_marker", spawn_event_marker_handler)
bind_handler("remove_event_marker", remove_event_marker_handler)
bind_handler("trigger_alarm", trigger_alarm_handler)
bind_handler("create_storm", create_storm_handler)
bind_handler("extinguish_storm", extinguish_storm_handler)
bind_handler("collapse_tunnel", collapse_tunnel_handler)
bind_handler("reinforce_tunnel", reinforce_tunnel_handler)
bind_handler("flood_area", flood_area_handler)
bind_handler("create_signal_fire", create_signal_fire_handler)
bind_handler("set_watch_lights", set_watch_lights_handler)
