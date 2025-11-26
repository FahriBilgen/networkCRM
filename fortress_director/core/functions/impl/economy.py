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


def allocate_food_handler(game_state: GameState, amount: int, target: str) -> Dict[str, Any]:
    delta = -abs(int(amount))
    remaining = game_state.adjust_metric("food", delta)
    log = f"{abs(delta)} food allocated to {target}. Remaining {remaining}."
    return _response(log, metrics={"food": delta}, effects={"target": target})


def ration_food_handler(game_state: GameState, severity: int) -> Dict[str, Any]:
    game_state.set_flag("rationing")
    morale_hit = -max(1, int(severity))
    game_state.adjust_metric("morale", morale_hit)
    log = f"Ration plan enacted at severity {severity}."
    return _response(log, metrics={"morale": morale_hit})


def gather_supplies_handler(
    game_state: GameState, region: str, effort: int
) -> Dict[str, Any]:
    gain = max(1, int(effort))
    total = game_state.adjust_metric("resources", gain)
    log = f"Supply teams gather {gain} resources from {region}."
    return _response(log, metrics={"resources": gain}, effects={"total_resources": total})


def craft_ammo_handler(
    game_state: GameState, workshop: str, batch: int
) -> Dict[str, Any]:
    produced = max(1, int(batch))
    game_state.adjust_metric("ammo", produced)
    game_state.adjust_world_stat("resources", -1)
    log = f"{workshop} crafts {produced} ammo batches."
    return _response(
        log,
        metrics={"ammo": produced, "resources": -1},
        effects={"workshop": workshop},
    )


def salvage_material_handler(
    game_state: GameState, location: str, amount: int
) -> Dict[str, Any]:
    gain = max(1, int(amount))
    game_state.adjust_metric("resources", gain)
    log = f"Salvage crews in {location} collect {gain} usable materials."
    return _response(log, metrics={"resources": gain})


def store_resources_handler(
    game_state: GameState, resource: str, amount: int
) -> Dict[str, Any]:
    stored = max(1, int(amount))
    game_state.adjust_metric(f"stored_{resource}", stored)
    log = f"Stored {stored} units of {resource}."
    return _response(log, effects={"resource": resource, "stored": stored})


def redistribute_stockpile_handler(
    game_state: GameState, from_stock: str, to_stock: str, amount: int
) -> Dict[str, Any]:
    delta = max(1, int(amount))
    game_state.adjust_metric(from_stock, -delta)
    game_state.adjust_metric(to_stock, delta)
    log = f"Redistributed {delta} from {from_stock} to {to_stock}."
    return _response(
        log,
        metrics={from_stock: -delta, to_stock: delta},
    )


def limit_consumption_handler(
    game_state: GameState, resource: str, percent: int
) -> Dict[str, Any]:
    game_state.set_flag(f"limit_{resource}")
    log = f"Consumption of {resource} limited by {percent}%."
    return _response(log, effects={"resource": resource, "limit": percent})


def boost_production_handler(
    game_state: GameState, workshop: str, focus: str
) -> Dict[str, Any]:
    game_state.add_state_tag(f"production_{focus}")
    resource_gain = 2
    game_state.adjust_metric("resources", resource_gain)
    log = f"{workshop} boosts production focused on {focus} (+{resource_gain})."
    return _response(
        log,
        metrics={"resources": resource_gain},
        effects={"workshop": workshop, "focus": focus},
    )


def check_inventory_handler(game_state: GameState, resource: str) -> Dict[str, Any]:
    metrics = game_state.snapshot().get("metrics", {})
    quantity = int(metrics.get(resource, 0) or 0)
    log = f"Inventory check: {resource} = {quantity}."
    return _response(log, effects={"resource": resource, "quantity": quantity})


bind_handler("allocate_food", allocate_food_handler)
bind_handler("ration_food", ration_food_handler)
bind_handler("gather_supplies", gather_supplies_handler)
bind_handler("craft_ammo", craft_ammo_handler)
bind_handler("salvage_material", salvage_material_handler)
bind_handler("store_resources", store_resources_handler)
bind_handler("redistribute_stockpile", redistribute_stockpile_handler)
bind_handler("limit_consumption", limit_consumption_handler)
bind_handler("boost_production", boost_production_handler)
bind_handler("check_inventory", check_inventory_handler)
