from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any, Callable, Dict, Iterable, List, Optional

from fortress_director.core.functions.function_schema import (
    FunctionParam,
    SafeFunctionMeta,
)
from fortress_director.themes.schema import ThemeConfig

LOGGER = logging.getLogger(__name__)

FUNCTION_REGISTRY: Dict[str, SafeFunctionMeta] = {}


def register_safe_function(meta: SafeFunctionMeta) -> None:
    """Register a SafeFunctionMeta entry in the global registry."""

    if meta.name in FUNCTION_REGISTRY:
        raise ValueError(f"Duplicate safe function: {meta.name}")
    FUNCTION_REGISTRY[meta.name] = meta


def bind_handler(name: str, handler: Callable[..., Dict[str, Any]]) -> SafeFunctionMeta:
    """Attach a runtime handler to a registered safe function."""

    if name not in FUNCTION_REGISTRY:
        raise KeyError(f"Safe function not registered: {name}")
    meta = FUNCTION_REGISTRY[name]
    meta.handler = handler
    return meta


def get_safe_function(name: str) -> Optional[SafeFunctionMeta]:
    return FUNCTION_REGISTRY.get(name)


def load_defaults() -> Dict[str, SafeFunctionMeta]:
    """Seed the registry with the canonical 60+ safe functions."""

    if FUNCTION_REGISTRY:
        return FUNCTION_REGISTRY
    for category, entries in _CATEGORY_DEFINITIONS.items():
        for entry in entries:
            register_safe_function(_build_meta(category, entry))
    return FUNCTION_REGISTRY


def _build_meta(category: str, entry: Dict[str, Any]) -> SafeFunctionMeta:
    params = [
        FunctionParam(
            name=param["name"],
            type=param["type"],
            required=param.get("required", True),
        )
        for param in entry.get("params", [])
    ]
    return SafeFunctionMeta(
        name=entry["name"],
        category=category,
        description=entry["description"],
        params=params,
        gas_cost=entry.get("gas_cost", 1),
        planner_weight=float(entry.get("planner_weight", 1.0)),
        enabled=bool(entry.get("enabled", True)),
    )


_CATEGORY_DEFINITIONS: Dict[str, List[Dict[str, Any]]] = {
    "combat": [
        {
            "name": "apply_combat_pressure",
            "description": "Increase perceived pressure on the defenders.",
            "params": [{"name": "intensity", "type": "int"}],
            "gas_cost": 3,
        },
        {
            "name": "reduce_threat",
            "description": "Lower the current threat score through tactics.",
            "params": [{"name": "amount", "type": "int"}],
            "gas_cost": 2,
        },
        {
            "name": "ranged_attack",
            "description": "Execute a ranged volley on the specified vector.",
            "params": [
                {"name": "target_area", "type": "str"},
                {"name": "intensity", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "melee_engagement",
            "description": "Order nearby units into hand-to-hand combat.",
            "params": [
                {"name": "attacker_ids", "type": "npc_id_list"},
                {"name": "defender_ids", "type": "npc_id_list"},
                {"name": "structure_id", "type": "structure_id"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "suppressive_fire",
            "description": "Lay down crossbow or cannon fire to hold enemies.",
            "params": [
                {"name": "sector", "type": "str"},
                {"name": "duration", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "scout_enemy_positions",
            "description": "Send eyes-on intel about hostile positioning.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "direction", "type": "str"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "fortify_combat_zone",
            "description": "Improve cover and footing in the named zone.",
            "params": [
                {"name": "zone", "type": "str"},
                {"name": "armor_boost", "type": "int"},
            ],
            "gas_cost": 4,
        },
        {
            "name": "deploy_archers",
            "description": "Position archers to rain arrows at coordinates.",
            "params": [
                {"name": "x", "type": "int"},
                {"name": "y", "type": "int"},
                {"name": "volleys", "type": "int", "required": False},
            ],
            "gas_cost": 3,
        },
        {
            "name": "set_ambush",
            "description": "Hide a unit for an ambush strike.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "x", "type": "int"},
                {"name": "y", "type": "int"},
            ],
            "gas_cost": 4,
        },
        {
            "name": "counter_attack",
            "description": "Launch a targeted counter assault.",
            "params": [
                {"name": "force", "type": "str"},
                {"name": "focus", "type": "str"},
            ],
            "gas_cost": 4,
        },
    ],
    "structure": [
        {
            "name": "reinforce_wall",
            "description": "Add reinforcement to a wall section.",
            "params": [
                {"name": "structure_id", "type": "str"},
                {"name": "amount", "type": "int", "required": False},
                {"name": "material", "type": "str", "required": False},
            ],
            "gas_cost": 3,
        },
        {
            "name": "repair_gate",
            "description": "Patch and balance the main gate.",
            "params": [
                {"name": "gate_id", "type": "str"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "patch_wall_section",
            "description": "Apply quick repairs to a wall subsection.",
            "params": [
                {"name": "section_id", "type": "str"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "strengthen_tower",
            "description": "Boost tower stability and spotting ability.",
            "params": [
                {"name": "tower_id", "type": "str"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "extinguish_fire",
            "description": "Deal with fires threatening a structure.",
            "params": [
                {"name": "structure_id", "type": "str"},
                {"name": "intensity", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "build_barricade",
            "description": "Assemble makeshift defenses in a corridor.",
            "params": [
                {"name": "location", "type": "str"},
                {"name": "materials", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "reinforce_trench",
            "description": "Deepen or stabilize a trench network.",
            "params": [
                {"name": "trench_id", "type": "str"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "deploy_defense_net",
            "description": "Install nets or chains against climbing.",
            "params": [
                {"name": "section_id", "type": "str"},
                {"name": "coverage", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "clear_rubble",
            "description": "Remove debris blocking access routes.",
            "params": [
                {"name": "section_id", "type": "str"},
                {"name": "effort", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "inspect_wall",
            "description": "Evaluate and log damage at a given wall section.",
            "params": [{"name": "section_id", "type": "str"}],
            "gas_cost": 1,
        },
    ],
    "npc": [
        {
            "name": "move_npc",
            "description": "Reposition an NPC to absolute coordinates.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "x", "type": "int"},
                {"name": "y", "type": "int"},
                {"name": "room", "type": "str", "required": False},
            ],
            "gas_cost": 2,
        },
        {
            "name": "assign_role",
            "description": "Change the operational role of an NPC.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "role", "type": "str"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "heal_npc",
            "description": "Restore health and morale for an NPC.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "rest_npc",
            "description": "Force an NPC to rest for a number of hours.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "duration", "type": "int"},
            ],
            "gas_cost": 1,
        },
        {
            "name": "increase_npc_focus",
            "description": "Raise a specialist's focus level.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "reduce_npc_focus",
            "description": "Reduce focus strain for an NPC.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "give_equipment",
            "description": "Hand new gear to an NPC.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "item", "type": "str"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "send_on_patrol",
            "description": "Dispatch an NPC on a patrol route.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "duration", "type": "int", "required": False},
            ],
            "gas_cost": 3,
        },
        {
            "name": "return_from_patrol",
            "description": "Recall an NPC from patrol and log intel.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "report", "type": "str", "required": False},
            ],
            "gas_cost": 2,
        },
        {
            "name": "rally_npc",
            "description": "Deliver a quick pep talk to an NPC.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "message", "type": "str", "required": False},
            ],
            "gas_cost": 1,
        },
    ],
    "economy": [
        {
            "name": "allocate_food",
            "description": "Distribute food stores to a target group.",
            "params": [
                {"name": "amount", "type": "int"},
                {"name": "target", "type": "str"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "ration_food",
            "description": "Apply rationing to conserve supplies.",
            "params": [{"name": "severity", "type": "int"}],
            "gas_cost": 2,
        },
        {
            "name": "gather_supplies",
            "description": "Send teams to gather external resources.",
            "params": [
                {"name": "region", "type": "str"},
                {"name": "effort", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "craft_ammo",
            "description": "Produce ammunition batches in the workshop.",
            "params": [
                {"name": "workshop", "type": "str"},
                {"name": "batch", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "salvage_material",
            "description": "Salvage debris for reusable materials.",
            "params": [
                {"name": "location", "type": "str"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "store_resources",
            "description": "Move resources into protected stores.",
            "params": [
                {"name": "resource", "type": "str"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 1,
        },
        {
            "name": "redistribute_stockpile",
            "description": "Transfer resources between stockpiles.",
            "params": [
                {"name": "from_stock", "type": "str"},
                {"name": "to_stock", "type": "str"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "limit_consumption",
            "description": "Cap consumption for a named resource.",
            "params": [
                {"name": "resource", "type": "str"},
                {"name": "percent", "type": "int"},
            ],
            "gas_cost": 1,
        },
        {
            "name": "boost_production",
            "description": "Focus a workshop on a critical output.",
            "params": [
                {"name": "workshop", "type": "str"},
                {"name": "focus", "type": "str"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "check_inventory",
            "description": "Report on the level of a resource.",
            "params": [{"name": "resource", "type": "str"}],
            "gas_cost": 1,
        },
    ],
    "morale": [
        {
            "name": "inspire_troops",
            "description": "Deliver an inspiring field speech.",
            "params": [
                {"name": "speech", "type": "str"},
                {"name": "bonus", "type": "int", "required": False},
            ],
            "gas_cost": 2,
        },
        {
            "name": "calm_civilians",
            "description": "Deploy mediators to calm civilians.",
            "params": [
                {"name": "zone", "type": "str"},
                {"name": "effort", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "hold_speech",
            "description": "Hold a formal speech at the keep.",
            "params": [
                {"name": "topic", "type": "str"},
                {"name": "audience", "type": "str"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "punish_treason",
            "description": "Discipline traitors to deter unrest.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "severity", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "reward_bravery",
            "description": "Reward an NPC for valor.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "reward", "type": "str"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "celebrate_small_victory",
            "description": "Mark a win to keep spirits high.",
            "params": [{"name": "location", "type": "str"}],
            "gas_cost": 1,
        },
        {
            "name": "reduce_panic",
            "description": "Apply emergency counseling to reduce panic.",
            "params": [
                {"name": "zone", "type": "str"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "hold_council_meeting",
            "description": "Gather leaders to discuss morale.",
            "params": [{"name": "agenda", "type": "str"}],
            "gas_cost": 2,
        },
        {
            "name": "comfort_wounded",
            "description": "Provide comfort to wounded units.",
            "params": [
                {"name": "ward", "type": "str"},
                {"name": "care", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "assign_morale_officer",
            "description": "Assign a morale officer to a sector.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "sector", "type": "str"},
            ],
            "gas_cost": 2,
        },
    ],
    "event": [
        {
            "name": "spawn_event_marker",
            "description": "Add a marker to the tactical map.",
            "params": [
                {"name": "marker_id", "type": "str"},
                {"name": "x", "type": "int"},
                {"name": "y", "type": "int"},
                {"name": "severity", "type": "int", "required": False},
            ],
            "gas_cost": 2,
        },
        {
            "name": "remove_event_marker",
            "description": "Remove an event marker by id.",
            "params": [{"name": "marker_id", "type": "str"}],
            "gas_cost": 1,
        },
        {
            "name": "trigger_alarm",
            "description": "Raise an alarm level and log it.",
            "params": [
                {"name": "level", "type": "str"},
                {"name": "message", "type": "str", "required": False},
            ],
            "gas_cost": 2,
        },
        {
            "name": "create_storm",
            "description": "Simulate a storm event around the fortress.",
            "params": [
                {"name": "duration", "type": "int"},
                {"name": "intensity", "type": "int"},
            ],
            "gas_cost": 4,
        },
        {
            "name": "extinguish_storm",
            "description": "Stabilize weather sensors and end storms.",
            "params": [{"name": "duration", "type": "int"}],
            "gas_cost": 3,
        },
        {
            "name": "collapse_tunnel",
            "description": "Collapse a suspicious tunnel route.",
            "params": [{"name": "tunnel_id", "type": "str"}],
            "gas_cost": 3,
        },
        {
            "name": "reinforce_tunnel",
            "description": "Stabilize an important tunnel.",
            "params": [
                {"name": "tunnel_id", "type": "str"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "flood_area",
            "description": "Flood a zone to slow intruders.",
            "params": [
                {"name": "zone", "type": "str"},
                {"name": "severity", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "create_signal_fire",
            "description": "Light a signal fire at a specified spot.",
            "params": [
                {"name": "location", "type": "str"},
                {"name": "intensity", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "set_watch_lights",
            "description": "Activate watch lights on the battlements.",
            "params": [
                {"name": "section", "type": "str"},
                {"name": "brightness", "type": "int"},
            ],
            "gas_cost": 1,
        },
    ],
    "utility": [
        {
            "name": "adjust_metric",
            "description": "Adjust a numeric metric by a delta.",
            "params": [
                {"name": "metric", "type": "str"},
                {"name": "delta", "type": "int"},
                {"name": "cause", "type": "str", "required": False},
            ],
            "gas_cost": 1,
        },
        {
            "name": "log_message",
            "description": "Append a formatted message to the log.",
            "params": [
                {"name": "message", "type": "str"},
                {"name": "severity", "type": "str", "required": False},
            ],
            "gas_cost": 1,
        },
        {
            "name": "tag_state",
            "description": "Attach a monitoring tag to the GameState.",
            "params": [{"name": "tag", "type": "str"}],
            "gas_cost": 1,
        },
        {
            "name": "set_flag",
            "description": "Enable a world flag for downstream agents.",
            "params": [{"name": "flag", "type": "str"}],
            "gas_cost": 1,
        },
        {
            "name": "clear_flag",
            "description": "Remove a world flag when it is no longer needed.",
            "params": [{"name": "flag", "type": "str"}],
            "gas_cost": 1,
        },
    ],
    "final_effects": [
        {
            "name": "trigger_mass_evacuate",
            "description": "Initiate emergency convoys that evacuate remaining civilians.",
            "params": [],
            "gas_cost": 1,
        },
        {
            "name": "collapse_structure",
            "description": "Force a cinematic collapse on the referenced structure.",
            "params": [{"name": "structure_id", "type": "structure_id"}],
            "gas_cost": 2,
        },
        {
            "name": "ignite_structure",
            "description": "Set the structure ablaze for dramatic flair.",
            "params": [{"name": "structure_id", "type": "structure_id"}],
            "gas_cost": 2,
        },
        {
            "name": "spawn_fire_effect",
            "description": "Spawn a large fire marker at map coordinates.",
            "params": [{"name": "x", "type": "int"}, {"name": "y", "type": "int"}],
            "gas_cost": 1,
        },
        {
            "name": "spawn_smoke_effect",
            "description": "Spawn a smoke bloom marker at map coordinates.",
            "params": [{"name": "x", "type": "int"}, {"name": "y", "type": "int"}],
            "gas_cost": 1,
        },
        {
            "name": "spawn_mass_enemy_wave",
            "description": "Telegraph a massed enemy wave from the specified direction.",
            "params": [
                {"name": "direction", "type": "str"},
                {"name": "strength", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "boost_allied_morale",
            "description": "Apply a map-wide morale shift for allied forces.",
            "params": [{"name": "delta", "type": "int"}],
            "gas_cost": 1,
        },
        {
            "name": "freeze_weather",
            "description": "Lock the battlefield weather in a frozen state.",
            "params": [{"name": "duration", "type": "int"}],
            "gas_cost": 2,
        },
        {
            "name": "global_blackout",
            "description": "Shut down every light source to create a blackout effect.",
            "params": [],
            "gas_cost": 2,
        },
        {
            "name": "npc_final_move",
            "description": "Move an NPC to a dramatic final coordinate.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "x", "type": "int"},
                {"name": "y", "type": "int"},
            ],
            "gas_cost": 1,
        },
    ],
    "diplomacy": [
        {
            "name": "propose_surrender",
            "description": "Send an envoy to demand enemy surrender.",
            "params": [
                {"name": "message", "type": "str"},
                {"name": "threat_level", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "establish_truce",
            "description": "Negotiate a ceasefire with opposing forces.",
            "params": [
                {"name": "duration", "type": "int"},
                {"name": "npc_id", "type": "npc_id"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "send_messenger",
            "description": "Dispatch a crucial message via envoy.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "target_area", "type": "str"},
                {"name": "message_content", "type": "str", "required": False},
            ],
            "gas_cost": 2,
        },
        {
            "name": "negotiate_alliance",
            "description": "Form an alliance with neutral parties or NPCs.",
            "params": [
                {"name": "faction_id", "type": "str"},
                {"name": "incentive_level", "type": "int"},
            ],
            "gas_cost": 4,
        },
        {
            "name": "spread_propaganda",
            "description": "Disseminate propaganda to weaken enemy morale.",
            "params": [
                {"name": "message", "type": "str"},
                {"name": "area_of_effect", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "broker_peace",
            "description": "Attempt to broker peace between warring factions.",
            "params": [
                {"name": "faction_a", "type": "str"},
                {"name": "faction_b", "type": "str"},
                {"name": "terms", "type": "str", "required": False},
            ],
            "gas_cost": 5,
        },
        {
            "name": "secure_hostage",
            "description": "Take a hostage to leverage negotiating power.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "holding_location", "type": "str"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "call_upon_allies",
            "description": "Request aid from allied forces in nearby regions.",
            "params": [
                {"name": "ally_faction", "type": "str"},
                {"name": "urgency", "type": "int"},
            ],
            "gas_cost": 2,
        },
    ],
    "crafting": [
        {
            "name": "forge_weapon",
            "description": "Craft a new weapon from available materials.",
            "params": [
                {"name": "weapon_type", "type": "str"},
                {"name": "quality", "type": "int"},
                {"name": "material", "type": "str", "required": False},
            ],
            "gas_cost": 3,
        },
        {
            "name": "brew_potion",
            "description": "Create a potion for beneficial effects.",
            "params": [
                {"name": "potion_type", "type": "str"},
                {"name": "potency", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "repair_armor",
            "description": "Restore damaged armor to serviceable condition.",
            "params": [
                {"name": "armor_id", "type": "str"},
                {"name": "repair_level", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "craft_siege_engine",
            "description": "Construct a siege weapon (catapult, ram).",
            "params": [
                {"name": "engine_type", "type": "str"},
                {"name": "location", "type": "str"},
                {"name": "construction_time", "type": "int", "required": False},
            ],
            "gas_cost": 4,
        },
        {
            "name": "create_trap",
            "description": "Construct a trap or snare in a specific location.",
            "params": [
                {"name": "trap_type", "type": "str"},
                {"name": "x", "type": "int"},
                {"name": "y", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "forge_armor",
            "description": "Craft new protective armor from raw materials.",
            "params": [
                {"name": "armor_type", "type": "str"},
                {"name": "quality", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "craft_explosive",
            "description": "Prepare explosive charges for combat.",
            "params": [
                {"name": "explosive_type", "type": "str"},
                {"name": "quantity", "type": "int"},
            ],
            "gas_cost": 3,
        },
    ],
    "magic": [
        {
            "name": "cast_barrier",
            "description": "Create a magical barrier to protect an area.",
            "params": [
                {"name": "barrier_type", "type": "str"},
                {"name": "strength", "type": "int"},
                {"name": "duration", "type": "int"},
            ],
            "gas_cost": 4,
        },
        {
            "name": "summon_guardian",
            "description": "Summon a guardian spirit to aid defenders.",
            "params": [
                {"name": "location", "type": "str"},
                {"name": "duration", "type": "int"},
            ],
            "gas_cost": 5,
        },
        {
            "name": "dispel_darkness",
            "description": "Use magic to illuminate a darkened area.",
            "params": [
                {"name": "area_id", "type": "str"},
                {"name": "intensity", "type": "int"},
            ],
            "gas_cost": 2,
        },
        {
            "name": "curse_enemy",
            "description": "Cast a curse to reduce enemy effectiveness.",
            "params": [
                {"name": "target_faction", "type": "str"},
                {"name": "curse_type", "type": "str"},
                {"name": "potency", "type": "int", "required": False},
            ],
            "gas_cost": 3,
        },
        {
            "name": "heal_wounded",
            "description": "Use magic to restore health to injured allies.",
            "params": [
                {"name": "area_of_effect", "type": "str"},
                {"name": "healing_power", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "teleport_npc",
            "description": "Magically transport an NPC to a distant location.",
            "params": [
                {"name": "npc_id", "type": "npc_id"},
                {"name": "destination", "type": "str"},
            ],
            "gas_cost": 4,
        },
        {
            "name": "create_illusion",
            "description": "Create a magical illusion to confuse enemies.",
            "params": [
                {"name": "illusion_type", "type": "str"},
                {"name": "area", "type": "str"},
                {"name": "duration", "type": "int"},
            ],
            "gas_cost": 3,
        },
        {
            "name": "drain_enemy_mana",
            "description": "Siphon magical energy from enemy spellcasters.",
            "params": [
                {"name": "target_npc", "type": "npc_id"},
                {"name": "amount", "type": "int"},
            ],
            "gas_cost": 3,
        },
    ],
}


DEFAULT_SAFE_FUNCTION_METADATA = load_defaults()


def apply_theme_overrides(
    registry: Dict[str, SafeFunctionMeta],
    theme: ThemeConfig | None,
) -> Dict[str, SafeFunctionMeta]:
    """Return a cloned registry with theme overrides applied."""

    if not registry:
        return {}
    themed: Dict[str, SafeFunctionMeta] = {}
    theme_id = getattr(theme, "id", None)
    theme_overrides = theme.safe_function_overrides if theme else {}
    for name, meta in registry.items():
        cloned = deepcopy(meta)
        override_payload: Dict[str, Any] = {}
        if theme_id and meta.theme_overrides.get(theme_id):
            override_payload.update(meta.theme_overrides[theme_id])
        if theme_overrides and name in theme_overrides:
            override_payload.update(theme_overrides[name])
        if "gas_cost" in override_payload:
            try:
                cloned.gas_cost = int(override_payload["gas_cost"])
            except (TypeError, ValueError):
                LOGGER.debug("Invalid gas_cost override for %s", name)
        if "enabled" in override_payload:
            cloned.enabled = bool(override_payload["enabled"])
        if "planner_weight" in override_payload:
            try:
                pw = override_payload["planner_weight"]
                cloned.planner_weight = float(pw)
            except (TypeError, ValueError):
                LOGGER.debug("Invalid planner_weight override for %s", name)
        if cloned.enabled:
            themed[name] = cloned
    return themed


class SafeFunctionRegistry:
    """Compatibility wrapper exposing the legacy registry interface."""

    def __init__(self) -> None:
        load_defaults()

    def list_metadata(self) -> Iterable[SafeFunctionMeta]:
        return FUNCTION_REGISTRY.values()

    def get_metadata(self, name: str) -> Optional[SafeFunctionMeta]:
        return FUNCTION_REGISTRY.get(name)
