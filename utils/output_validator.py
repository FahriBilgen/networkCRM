"""Schema validation helpers for orchestrator turn outputs."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


class OutputValidationError(ValueError):
    """Raised when turn output does not match the expected structure."""


def _require_keys(
    payload: Dict[str, Any], *, keys: Iterable[str], context: str
) -> None:
    for key in keys:
        if key not in payload:
            raise OutputValidationError(f"Missing key '{key}' in {context}")


def _assert_type(value: Any, expected_type: type, *, context: str) -> None:
    if not isinstance(value, expected_type):
        message = f"{context} must be of type {expected_type.__name__}"
        raise OutputValidationError(message)


def _validate_options(options: List[Dict[str, Any]]) -> None:
    if not options:
        raise OutputValidationError("Event options list cannot be empty")
    for idx, option in enumerate(options):
        context = f"event option {idx}"
        _require_keys(
            option,
            keys=("id", "text", "action_type"),
            context=context,
        )
        all_strings = all(
            isinstance(option[key], str) and option[key].strip()
            for key in ("id", "text", "action_type")
        )
        if not all_strings:
            message = f"{context} fields must be non-empty strings"
            raise OutputValidationError(message)


def _validate_character_reactions(reactions: List[Dict[str, Any]]) -> None:
    for idx, reaction in enumerate(reactions):
        context = f"character reaction {idx}"
        _require_keys(
            reaction,
            keys=("name", "intent", "action", "speech"),
            context=context,
        )
        for key in ("name", "intent", "action", "speech"):
            if not isinstance(reaction.get(key), str):
                message = f"{context} field '{key}' must be a string"
                raise OutputValidationError(message)
        effects = reaction.get("effects", {})
        if effects is None:
            continue
        if not isinstance(effects, dict):
            message = f"{context} effects must be an object if present"
            raise OutputValidationError(message)


def validate_turn_output(payload: Dict[str, Any]) -> None:
    """Validate the structure of the orchestrator turn output."""

    if not isinstance(payload, dict):
        raise OutputValidationError("Turn output must be a JSON object")

    _require_keys(
        payload,
        keys=(
            "world",
            "event",
            "player_choice",
            "character_reactions",
            "metrics_after",
            "glitch",
            "logs",
            "win_loss",
            "narrative",
        ),
        context="root payload",
    )

    world = payload["world"]
    _assert_type(world, dict, context="world")
    _require_keys(
        world,
        keys=("atmosphere", "sensory_details"),
        context="world",
    )
    world_strings = all(
        isinstance(world[key], str) for key in ("atmosphere", "sensory_details")
    )
    if not world_strings:
        raise OutputValidationError("World fields must be strings")

    event = payload["event"]
    _assert_type(event, dict, context="event")
    _require_keys(
        event,
        keys=("scene", "options", "major_event"),
        context="event",
    )
    if not isinstance(event["scene"], str):
        raise OutputValidationError("Event scene must be a string")
    if not isinstance(event["major_event"], bool):
        raise OutputValidationError("Event major_event must be boolean")
    options = event["options"]
    _assert_type(options, list, context="event options")
    if options:
        _validate_options(options)
    else:
        player_choice = payload.get("player_choice", {})
        action_type = player_choice.get("action_type") if isinstance(player_choice, dict) else None
        if action_type != "end":
            raise OutputValidationError(
                "Event options list cannot be empty unless ending the campaign"
            )

    player_choice = payload["player_choice"]
    _assert_type(player_choice, dict, context="player_choice")
    _require_keys(
        player_choice,
        keys=("id", "text", "action_type"),
        context="player_choice",
    )
    choice_strings = all(
        isinstance(player_choice[key], str) and player_choice[key].strip()
        for key in ("id", "text", "action_type")
    )
    if not choice_strings:
        raise OutputValidationError("Player choice fields must be non-empty strings")

    reactions = payload["character_reactions"]
    _assert_type(reactions, list, context="character_reactions")
    _validate_character_reactions(reactions)

    warnings = payload.get("warnings")
    if warnings is not None:
        _assert_type(warnings, list, context="warnings")
        for warning in warnings:
            if not isinstance(warning, str):
                raise OutputValidationError("Warnings must be strings")

    metrics_after = payload["metrics_after"]
    _assert_type(metrics_after, dict, context="metrics_after")
    required_metrics = (
        "order",
        "morale",
        "resources",
        "knowledge",
        "corruption",
        "glitch",
    )
    for metric in required_metrics:
        if metric not in metrics_after:
            raise OutputValidationError(f"metrics_after missing '{metric}'")
        value = metrics_after[metric]
        if not isinstance(value, int):
            raise OutputValidationError(
                f"metrics_after['{metric}'] must be an integer"
            )

    glitch = payload["glitch"]
    _assert_type(glitch, dict, context="glitch")
    _require_keys(glitch, keys=("roll", "effects"), context="glitch")
    if not isinstance(glitch["roll"], int):
        raise OutputValidationError("glitch.roll must be an integer")
    effects = glitch["effects"]
    _assert_type(effects, list, context="glitch effects")
    for effect in effects:
        if not isinstance(effect, str):
            raise OutputValidationError("glitch effects must be strings")

    logs = payload["logs"]
    _assert_type(logs, list, context="logs")
    for entry in logs:
        if not isinstance(entry, dict):
            raise OutputValidationError("log entries must be objects")
        _require_keys(
            entry,
            keys=("metric", "delta", "value", "cause"),
            context="log entry",
        )

    win_loss = payload["win_loss"]
    _assert_type(win_loss, dict, context="win_loss")
    _require_keys(win_loss, keys=("status", "reason"), context="win_loss")
    status = win_loss["status"]
    if status not in {"ongoing", "win", "loss"}:
        raise OutputValidationError("win_loss.status must be ongoing, win, or loss")
    for key in ("status", "reason"):
        if not isinstance(win_loss[key], str):
            raise OutputValidationError(f"win_loss.{key} must be a string")

    narrative = payload["narrative"]
    if not isinstance(narrative, str):
        raise OutputValidationError("narrative must be a string")
