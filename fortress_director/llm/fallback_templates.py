"""LLM fallback templates for graceful degradation when LLM times out."""

from typing import Any, Dict

# Fallback templates for when LLM calls timeout


def fallback_director_intent() -> Dict[str, Any]:
    """Fallback scene intent when director agent times out."""
    return {
        "scene_intent": {
            "atmosphere": "tension",
            "npc_focus": "default",
            "player_agency": "explore",
        },
        "fallback_triggered": True,
    }


def fallback_planner_actions(
    projected_state: Dict[str, Any],
) -> Dict[str, Any]:
    """Fallback planned actions when planner agent times out."""
    # Return minimal valid action list
    return {
        "planned_actions": [
            {
                "function": "wait_turn",
                "args": {},
                "explanation": "Waiting for system to respond",
            }
        ],
        "fallback_triggered": True,
    }


def fallback_renderer_narrative(
    world_state: Dict[str, Any],
) -> Dict[str, Any]:
    """Fallback narrative when world renderer times out."""
    threat_level = world_state.get("metrics", {}).get("threat", 0)
    morale = world_state.get("metrics", {}).get("morale", 0)

    if threat_level > 70:
        narrative = "The siege tightens. Enemies press forward relentlessly. "
        narrative += "Every moment counts."
    elif morale < 20:
        narrative = "Despair hangs heavy. Hope fades with each passing turn. "
        narrative += "The situation grows dire."
    else:
        narrative = (
            "The settlement holds on, battered but not broken. "
            "You assess your options carefully."
        )

    return {
        "narrative": narrative,
        "atmosphere": {
            "visual_tone": "siege",
            "emotional_weight": "tension",
        },
        "fallback_triggered": True,
    }


def should_trigger_fallback(
    elapsed_time: float,
    timeout_threshold: float = 29.0,
) -> bool:
    """
    Check if we should trigger fallback based on elapsed time.

    Args:
        elapsed_time: Seconds since turn started
        timeout_threshold: Seconds before assuming LLM will timeout

    Returns:
        True if we should use fallback
    """
    return elapsed_time > timeout_threshold
