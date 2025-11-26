"""Map a validated player action into a planner-friendly context.

Output shape:
{
  "player_intent": "repair structure western_wall",
  "required_calls": [
    {"function": "reinforce_wall", "args": {"structure_id": "western_wall"}}
  ]
}
"""

from __future__ import annotations

from typing import Any, Dict, List


def route_player_action(
    action_id: str, params: Dict[str, Any], catalog_entry: Dict[str, Any]
) -> Dict[str, Any]:
    """Produce a minimal player action context for the planner.

    - `player_intent` is a short, strict NL string (no explanation).
    - `required_calls` is a list of dicts with `function` and `args`.
    """
    safe_fn = catalog_entry.get("safe_function") or ""
    args_map = catalog_entry.get("args_map") or {}

    # build args for the safe function by mapping args_map keys to either
    # values from params or literal constants in the map value
    mapped_args: Dict[str, Any] = {}
    for out_key, map_val in args_map.items():
        if isinstance(map_val, str) and map_val in params:
            mapped_args[out_key] = params.get(map_val)
        else:
            # literal or missing mapping -> use as-is
            mapped_args[out_key] = map_val

    # build a strict intent string: <verb> <noun> <primary_id>
    # derive verb from the action id where possible
    verb = action_id.split("_")[0]
    primary = mapped_args.get("structure_id") or mapped_args.get("npc_id") or ""
    # try to infer a compact noun from the catalog label (e.g. "Repair Wall" -> wall)
    label = str(catalog_entry.get("label") or "").strip()
    noun = "structure"
    if label:
        parts = label.split()
        if len(parts) >= 2:
            noun = parts[-1].lower()
    # normalize intent: prefer the compact noun when possible
    if mapped_args.get("structure_id"):
        player_intent = f"{verb} {noun} {primary}"
    elif mapped_args.get("npc_id") and mapped_args.get("activity"):
        player_intent = f"{verb} npc {primary}"
    elif mapped_args.get("npc_id"):
        player_intent = f"{verb} npc {primary}"
    else:
        player_intent = f"{verb} {primary}".strip()

    required_calls: List[Dict[str, Any]] = [
        {"function": safe_fn, "args": mapped_args},
    ]

    return {"player_intent": player_intent, "required_calls": required_calls}
