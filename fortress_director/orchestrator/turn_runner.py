"""Helper routines for orchestrator turn flow."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fortress_director.utils.metrics_manager import MetricManager
from fortress_director.utils.output_validator import validate_turn_output

LOGGER = logging.getLogger(__name__)


def handle_finalized_game(orchestrator: Any, state_snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return an early result payload if the campaign is already finalized."""

    if not state_snapshot.get("finalized", False):
        return None

    LOGGER.info("Game already finalized, terminating turn early.")
    metric_manager = MetricManager(
        state_snapshot,
        log_sink=orchestrator._metric_log_sink(),
    )
    metrics_after = metric_manager.snapshot()
    world = {
        "atmosphere": "The campaign has concluded.",
        "sensory_details": "All is quiet across Lornhaven.",
    }
    result = {
        "WORLD_CONTEXT": orchestrator._build_world_context(state_snapshot),
        "scene": "The campaign has concluded.",
        "options": [],
        "world": world,
        "event": {"scene": "", "options": [], "major_event": False},
        "player_choice": {
            "id": "end",
            "text": "Campaign ended.",
            "action_type": "end",
        },
        "character_reactions": [],
        "npcs": orchestrator.build_npcs_for_ui(state_snapshot),
        "safe_function_history": [],
        "room_history": orchestrator.build_room_history(state_snapshot),
        "summary_text": state_snapshot.get("summary_text", ""),
        "metrics_after": metrics_after,
        "glitch": {"roll": 0, "effects": []},
        "logs": list(orchestrator._metric_log_buffer),
        "win_loss": {"status": "loss", "reason": "game_over"},
        "narrative": "Campaign ended.",
    }
    try:
        world["atmosphere"] = orchestrator._clean_text(world["atmosphere"])
        world["sensory_details"] = orchestrator._clean_text(world["sensory_details"])
        result["scene"] = orchestrator._clean_text(result["scene"])
        result["narrative"] = orchestrator._clean_text(result["narrative"])
    except Exception:
        pass
    validate_turn_output(result)
    return result


def handle_end_flag(orchestrator: Any, state_snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a minimal payload if an explicit end flag is set."""

    flags = state_snapshot.get("flags", [])
    if "end" not in flags:
        return None

    LOGGER.info("End flag detected, terminating early")
    return {
        "WORLD_CONTEXT": orchestrator._build_world_context(state_snapshot),
        "scene": "The campaign has concluded.",
        "options": [],
        "world": {},
        "event": {},
        "player_choice": {
            "id": "end",
            "text": "Campaign ended.",
            "action_type": "end",
        },
        "character_reactions": [],
        "npcs": orchestrator.build_npcs_for_ui(state_snapshot),
        "safe_function_history": [],
        "room_history": orchestrator.build_room_history(state_snapshot),
        "summary_text": state_snapshot.get("summary_text", ""),
        "metrics_after": state_snapshot.get("metrics", {}),
        "glitch": {"roll": 0, "effects": []},
        "logs": list(orchestrator._metric_log_buffer),
        "win_loss": {"status": "loss", "reason": "game_over"},
        "narrative": "Campaign ended.",
    }
