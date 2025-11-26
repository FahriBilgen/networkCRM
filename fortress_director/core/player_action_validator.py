"""Validate incoming player actions against the catalog and current GameState."""

from __future__ import annotations

from typing import Any, Dict, List

from fortress_director.core import player_action_catalog
from fortress_director.core.state_store import GameState


def _is_int_like(val: Any) -> bool:
    try:
        int(val)
        return True
    except (TypeError, ValueError):
        return False


def _coerce_coordinate(value: Any, name: str) -> int:
    if not _is_int_like(value):
        raise ValueError(f"missing parameter: {name}")
    return int(value)


def _coerce_id_list(value: Any, name: str) -> List[str]:
    if value is None:
        raise ValueError(f"missing parameter: {name}")
    if isinstance(value, (list, tuple, set)):
        result = [str(entry) for entry in value if entry]
    else:
        result = [str(value)]
    if not result:
        raise ValueError(f"missing parameter: {name}")
    return result


def validate_player_action(
    action_id: str, params: Dict[str, Any], game_state: GameState
) -> Dict[str, Any]:
    """Validate the player action and return a sanitized param mapping.

    Raises ValueError with messages like:
      - "missing parameter: x"
      - "npc not found: N001"
      - "structure not found: wall_2"
    """
    if not action_id:
        raise ValueError("missing parameter: action_id")
    catalog_entry = player_action_catalog.get_action_by_id(action_id)
    if catalog_entry is None:
        raise ValueError(f"unknown action: {action_id}")

    params = dict(params or {})

    # domain validations: run early so missing domain entities are
    # reported before missing-parameter errors
    # npc existence
    if "npc_id" in params:
        npc_id = params.get("npc_id")
        if not npc_id or game_state.get_npc(str(npc_id)) is None:
            raise ValueError(f"npc not found: {npc_id}")
    if "attacker_ids" in params:
        attacker_ids = _coerce_id_list(params.get("attacker_ids"), "attacker_ids")
        for npc in attacker_ids:
            if game_state.get_npc(str(npc)) is None:
                raise ValueError(f"npc not found: {npc}")
        params["attacker_ids"] = attacker_ids
    if "defender_ids" in params:
        defender_ids = _coerce_id_list(params.get("defender_ids"), "defender_ids")
        for npc in defender_ids:
            if game_state.get_npc(str(npc)) is None:
                raise ValueError(f"npc not found: {npc}")
        params["defender_ids"] = defender_ids
    # structure existence
    if "structure_id" in params:
        struct_id = params.get("structure_id")
        if not struct_id or game_state.get_structure(str(struct_id)) is None:
            raise ValueError(f"structure not found: {struct_id}")

    # check required params
    for req in catalog_entry.get("requires") or []:
        if req not in params:
            raise ValueError(f"missing parameter: {req}")

    # simple type checks for coordinates
    if "x" in params:
        params["x"] = _coerce_coordinate(params.get("x"), "x")
    if "y" in params:
        params["y"] = _coerce_coordinate(params.get("y"), "y")

    return params
