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


def reinforce_wall_handler(
    game_state: GameState,
    structure_id: str,
    amount: int,
    material: str | None = None,
) -> Dict[str, Any]:
    struct = game_state.adjust_structure_integrity(
        structure_id, int(amount), kind="wall"
    )
    if material:
        game_state.update_structure(struct.id, status=f"reinforced_{material}")
    log = f"Wall segment {structure_id} reinforced by {amount}."
    return _response(
        log,
        effects={"structure_id": structure_id, "integrity": struct.integrity},
    )


def repair_gate_handler(game_state: GameState, gate_id: str, amount: int) -> Dict[str, Any]:
    struct = game_state.adjust_structure_integrity(gate_id, int(amount), kind="gate")
    game_state.update_structure(gate_id, status="operational")
    log = f"Gate {gate_id} repaired (+{amount})."
    return _response(log, effects={"structure_id": gate_id, "integrity": struct.integrity})


def patch_wall_section_handler(
    game_state: GameState, section_id: str, amount: int
) -> Dict[str, Any]:
    struct = game_state.adjust_structure_integrity(section_id, int(amount), kind="wall")
    log = f"Wall section {section_id} patched by {amount}."
    return _response(log, effects={"structure_id": section_id, "integrity": struct.integrity})


def strengthen_tower_handler(
    game_state: GameState, tower_id: str, amount: int
) -> Dict[str, Any]:
    struct = game_state.adjust_structure_integrity(tower_id, int(amount), kind="tower")
    game_state.update_structure(tower_id, status="reinforced")
    log = f"Tower {tower_id} strengthened by {amount}."
    return _response(log, effects={"structure_id": tower_id, "integrity": struct.integrity})


def extinguish_fire_handler(
    game_state: GameState, structure_id: str, intensity: int
) -> Dict[str, Any]:
    struct = game_state.update_structure(structure_id, status="fire_out")
    morale_boost = max(1, int(intensity) // 2)
    game_state.adjust_metric("morale", morale_boost)
    log = f"Fire at {structure_id} extinguished."
    return _response(
        log,
        metrics={"morale": morale_boost},
        effects={"structure_id": structure_id, "status": struct.status},
    )


def build_barricade_handler(
    game_state: GameState, location: str, materials: int
) -> Dict[str, Any]:
    barricade_id = f"barricade_{location}"
    struct = game_state.adjust_structure_integrity(
        barricade_id, max(1, int(materials)), kind="barricade"
    )
    game_state.update_structure(barricade_id, status="blocking")
    log = f"Barricade erected at {location}."
    return _response(
        log,
        effects={"structure_id": barricade_id, "integrity": struct.integrity},
    )


def reinforce_trench_handler(
    game_state: GameState, trench_id: str, amount: int
) -> Dict[str, Any]:
    struct = game_state.adjust_structure_integrity(trench_id, int(amount), kind="trench")
    log = f"Trench {trench_id} reinforced."
    return _response(
        log,
        effects={"structure_id": trench_id, "integrity": struct.integrity},
    )


def deploy_defense_net_handler(
    game_state: GameState, section_id: str, coverage: int
) -> Dict[str, Any]:
    net_id = f"defense_net_{section_id}"
    struct = game_state.adjust_structure_integrity(
        net_id, max(1, int(coverage)), kind="netting"
    )
    game_state.update_structure(net_id, status="active")
    log = f"Defense net deployed over {section_id}."
    return _response(
        log,
        effects={"structure_id": net_id, "integrity": struct.integrity},
    )


def clear_rubble_handler(
    game_state: GameState, section_id: str, effort: int
) -> Dict[str, Any]:
    resources = min(0, -abs(int(effort)))
    game_state.adjust_metric("resources", resources)
    game_state.add_state_tag(f"cleared_{section_id}")
    log = f"Rubble cleared at {section_id}."
    return _response(
        log,
        metrics={"resources": resources},
        effects={"section": section_id},
    )


def inspect_wall_handler(game_state: GameState, section_id: str) -> Dict[str, Any]:
    struct = game_state.as_domain().structures.get(section_id)
    integrity = struct.integrity if struct else 0
    game_state.add_log_entry(f"Inspection report for {section_id}: {integrity} integrity.")
    game_state.add_state_tag(f"inspected_{section_id}")
    log = f"Inspection complete for {section_id}."
    return _response(log, effects={"structure_id": section_id, "integrity": integrity})


bind_handler("reinforce_wall", reinforce_wall_handler)
bind_handler("repair_gate", repair_gate_handler)
bind_handler("patch_wall_section", patch_wall_section_handler)
bind_handler("strengthen_tower", strengthen_tower_handler)
bind_handler("extinguish_fire", extinguish_fire_handler)
bind_handler("build_barricade", build_barricade_handler)
bind_handler("reinforce_trench", reinforce_trench_handler)
bind_handler("deploy_defense_net", deploy_defense_net_handler)
bind_handler("clear_rubble", clear_rubble_handler)
bind_handler("inspect_wall", inspect_wall_handler)
