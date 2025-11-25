from __future__ import annotations

from fortress_director.core.final_safe_functions import (
    boost_allied_morale_handler,
    collapse_structure_handler,
    freeze_weather_handler,
    global_blackout_handler,
    ignite_structure_handler,
    npc_final_move_handler,
    spawn_fire_effect_handler,
    spawn_mass_enemy_wave_handler,
    spawn_smoke_effect_handler,
    trigger_mass_evacuate_handler,
)
from fortress_director.core.state_store import GameState


def test_trigger_mass_evacuate_boosts_morale() -> None:
    state = GameState()
    before = state.snapshot()["metrics"]["morale"]
    result = trigger_mass_evacuate_handler(state)
    after = state.snapshot()["metrics"]["morale"]
    assert after > before
    assert result["effects"]["civilians_evacuated"] > 0


def test_structure_collapses_and_ignites() -> None:
    state = GameState()
    collapse_structure_handler(state, "inner_gate")
    ignite_structure_handler(state, "inner_gate")
    struct = state.get_structure("inner_gate")
    assert struct is not None
    assert struct.status in {"collapsed", "burning"}
    assert struct.on_fire is True


def test_spawn_visual_effects_add_markers() -> None:
    state = GameState()
    fire_result = spawn_fire_effect_handler(state, 2, 3)
    smoke_result = spawn_smoke_effect_handler(state, 4, 5)
    assert fire_result["effects"]["marker_id"] != smoke_result["effects"]["marker_id"]


def test_enemy_wave_and_morale_boost_adjust_metrics() -> None:
    state = GameState()
    morale_before = state.snapshot()["metrics"]["morale"]
    boost_allied_morale_handler(state, 5)
    assert state.snapshot()["metrics"]["morale"] >= morale_before + 5
    spawn_mass_enemy_wave_handler(state, direction="north", strength=42)
    world = state.snapshot().get("world") or {}
    assert "stability" in world


def test_freeze_weather_and_blackout() -> None:
    state = GameState()
    freeze_weather_handler(state, duration=4)
    weather = state.snapshot().get("weather_pattern")
    assert weather and weather["pattern"] == "frozen"
    global_blackout_handler(state)
    world = state.snapshot().get("world") or {}
    assert world.get("threat_level") == "blackout"


def test_npc_final_move_updates_coordinates() -> None:
    state = GameState()
    npc = state.snapshot()["npc_locations"][0]
    npc_final_move_handler(state, npc["id"], 7, 8)
    updated = state.get_npc(npc["id"])
    assert updated.x == 7 and updated.y == 8
