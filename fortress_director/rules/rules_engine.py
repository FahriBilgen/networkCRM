"""Deterministic rule processing for character-driven world updates."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from fortress_director.agents.base_agent import AgentError
from fortress_director.agents.judge_agent import JudgeAgent


LOGGER = logging.getLogger(__name__)


class RulesEngineError(RuntimeError):
    """Base class for rules engine failures."""


class TierOneValidationError(RulesEngineError):
    """Raised when structural constraints are violated."""


class TierTwoValidationError(RulesEngineError):
    """Raised when the judge detects lore inconsistencies."""


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


@dataclass
class RulesEngine:
    """Validates and applies character-driven changes to the world state."""

    judge_agent: JudgeAgent
    trust_floor: int = -5
    trust_ceiling: int = 5
    tolerance: int = 0

    def __init__(self, judge_agent: JudgeAgent, tolerance: int = 0):
        self.judge_agent = judge_agent
        self.tolerance = tolerance
        self.trust_floor = -5
        self.trust_ceiling = 5

    def process(
        self,
        *,
        state: Dict[str, Any],
        character_events: Iterable[Dict[str, Any]],
        world_context: str,
        scene: str,
        player_choice: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply validated character events to the world state copy. Logs every step."""
        LOGGER.info("RulesEngine.process called.")
        LOGGER.debug("Input state: %s", state)
        LOGGER.debug("Character events: %s", character_events)
        LOGGER.debug(
            "World context: %s, scene: %s, player_choice: %s",
            world_context,
            scene,
            player_choice,
        )
        try:
            events = self._validate_tier_one(character_events)
            LOGGER.info("Tier one validation passed.")
            self._validate_tier_two(events, world_context, scene, player_choice, state)
            LOGGER.info("Tier two validation passed.")
            new_state = deepcopy(state)
            applied_flags = set()
            for entry in events:
                effects = entry.get("effects", {}) or {}
                name = entry.get("name", "unknown")
                LOGGER.debug("Applying effects for %s: %s", name, effects)
                self._apply_trust(new_state, name, effects.get("trust_delta"))
                self._apply_logic_delta(new_state, effects.get("logic_delta"))
                self._apply_emotion_delta(new_state, effects.get("emotion_delta"))
                applied_flags.update(
                    self._apply_flags(new_state, effects.get("flag_set"))
                )
                self._apply_item_change(new_state, effects.get("item_change"))
                self._apply_status_change(new_state, effects.get("status_change"))
            self._update_metrics(new_state, player_choice, applied_flags)
            LOGGER.info("State updated by rules engine.")
            LOGGER.debug("Output state: %s", new_state)
            return new_state
        except Exception as exc:
            LOGGER.error("Exception in RulesEngine.process: %s", exc, exc_info=True)
            raise

    def _validate_tier_one(
        self, character_events: Iterable[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        LOGGER.info("RulesEngine._validate_tier_one called.")
        events: List[Dict[str, Any]] = []
        for idx, entry in enumerate(character_events):
            LOGGER.debug("Validating character event %d: %s", idx, entry)
            if not isinstance(entry, dict):
                raise TierOneValidationError(f"Entry {idx} is not a dict")

            required_fields = ["name", "intent", "action", "speech"]
            for field in required_fields:
                if field not in entry or not isinstance(entry[field], str):
                    raise TierOneValidationError(
                        f"Entry {idx} missing required field '{field}'"
                    )

            speech = entry.get("speech", "")
            if len(speech) > 200:
                raise TierOneValidationError(
                    f"Speech for '{entry['name']}' exceeds 200 characters"
                )

            effects = entry.get("effects") or {}
            if not isinstance(effects, dict):
                raise TierOneValidationError(
                    f"Effects for '{entry['name']}' must be an object"
                )

            trust_delta = effects.get("trust_delta")
            if trust_delta is not None and trust_delta not in (-1, 0, 1):
                raise TierOneValidationError(
                    f"Invalid trust_delta for '{entry['name']}': {trust_delta}"
                )

            flag_set = effects.get("flag_set")
            if flag_set is not None:
                if not isinstance(flag_set, list) or not all(
                    isinstance(flag, str) and flag for flag in flag_set
                ):
                    raise TierOneValidationError(
                        f"flag_set for {entry['name']} must be list[str]"
                    )

            item_change = effects.get("item_change")
            if item_change is not None:
                if not isinstance(item_change, dict):
                    raise TierOneValidationError(
                        f"item_change for {entry['name']} must be an object"
                    )
                required_item_fields = {"item", "delta", "target"}
                if not required_item_fields.issubset(item_change):
                    raise TierOneValidationError(
                        f"item_change for {entry['name']} missing fields"
                    )
                if item_change.get("delta") not in (-1, 1):
                    message = ("item_change delta for {name} must be -1 or 1").format(
                        name=entry["name"]
                    )
                    raise TierOneValidationError(message)

            status_change = effects.get("status_change")
            if status_change is not None:
                if not isinstance(status_change, dict):
                    raise TierOneValidationError(
                        f"status_change for {entry['name']} must be an object"
                    )
                if "duration" in status_change and status_change["duration"] < 0:
                    message = ("status_change duration for {name} must be >= 0").format(
                        name=entry["name"]
                    )
                    raise TierOneValidationError(message)

            events.append(entry)
        return events

    def _validate_tier_two(
        self,
        events: Iterable[Dict[str, Any]],
        world_context: str,
        scene: str,
        player_choice: Dict[str, Any],
        state: Dict[str, Any] = None,
    ) -> None:
        choice_summary: Dict[str, Any] = {}
        if isinstance(player_choice, dict):
            for key in ("id", "text", "action_type"):
                value = player_choice.get(key)
                if isinstance(value, str) and value:
                    choice_summary[key] = value

        # Ekstra context: flags ve status_effects
        flags = []
        status_effects = []
        if state:
            flags = state.get("flags", [])
            status_effects = state.get("status_effects", [])

        for entry in events:
            summary = self._build_judge_summary(entry, scene, choice_summary)
            try:
                judge_context = {
                    "WORLD_CONTEXT": world_context,
                    "content": summary,
                }
                if flags:
                    judge_context["flags"] = flags
                if status_effects:
                    judge_context["status_effects"] = status_effects
                # Pass tolerance to JudgeAgent if supported
                if hasattr(self.judge_agent, "tolerance"):
                    self.judge_agent.tolerance = self.tolerance
                verdict = self.judge_agent.evaluate(judge_context)
            except AgentError as exc:  # pragma: no cover - defensive
                raise TierTwoValidationError(f"Judge call failed: {exc}") from exc

            LOGGER.debug(
                "Judge verdict for %s: %s",
                entry.get("name"),
                verdict,
            )

            if not verdict.get("consistent", True):
                reason = verdict.get("reason", "unknown reason")
                raise TierTwoValidationError(
                    f"Judge rejected update for '{entry['name']}': {reason}"
                )

    def _build_judge_summary(
        self,
        entry: Dict[str, Any],
        scene: str,
        choice_summary: Dict[str, Any],
    ) -> str:
        effects = entry.get("effects", {})
        judgement_payload = {
            "scene": scene,
            "player_choice": choice_summary,
            "character_update": {
                "name": entry.get("name"),
                "intent": entry.get("intent"),
                "action": entry.get("action"),
                "speech": entry.get("speech"),
                "effects": effects,
            },
        }
        return json.dumps(judgement_payload)

    def _apply_trust(
        self,
        state: Dict[str, Any],
        character_name: str,
        trust_delta: Any,
    ) -> None:
        if trust_delta in (-1, 0, 1):
            trust = state.setdefault("npc_trust", {})
            current = trust.get(character_name, 0)
            trust[character_name] = _clamp(
                current + int(trust_delta),
                self.trust_floor,
                self.trust_ceiling,
            )

    def _apply_logic_delta(
        self,
        state: Dict[str, Any],
        logic_delta: Any,
    ) -> None:
        if logic_delta in (-1, 0, 1):
            scores = state.setdefault("scores", {})
            current = scores.get("logic_score", 0)
            scores["logic_score"] = _clamp(
                current + int(logic_delta),
                0,
                100,
            )

    def _apply_emotion_delta(
        self,
        state: Dict[str, Any],
        emotion_delta: Any,
    ) -> None:
        if emotion_delta in (-1, 0, 1):
            scores = state.setdefault("scores", {})
            current = scores.get("emotion_score", 0)
            scores["emotion_score"] = _clamp(
                current + int(emotion_delta),
                0,
                100,
            )

    def _apply_flags(self, state: Dict[str, Any], flags: Any) -> List[str]:
        if not flags:
            return []
        valid_flags = [flag for flag in _ensure_list(flags) if isinstance(flag, str)]
        if not valid_flags:
            return []
        existing = state.setdefault("flags", [])
        for flag in valid_flags:
            if flag not in existing:
                existing.append(flag)
        return valid_flags

    def _apply_item_change(self, state: Dict[str, Any], change: Any) -> None:
        if not isinstance(change, dict):
            return

        item = change.get("item")
        delta = change.get("delta")
        target = change.get("target")
        if not item or delta not in (-1, 1) or not target:
            return

        if target == "player":
            inventory = state.setdefault("player", {}).setdefault("inventory", [])
            if delta > 0:
                inventory.append(item)
            elif item in inventory:
                inventory.remove(item)
        else:
            storage = state.setdefault("items", {})
            targets = storage.setdefault(target, [])
            if delta > 0:
                targets.append(item)
            elif item in targets:
                targets.remove(item)

    def _apply_status_change(self, state: Dict[str, Any], change: Any) -> None:
        if not isinstance(change, dict):
            return

        effect = {
            "target": change.get("target"),
            "status": change.get("status"),
            "duration": change.get("duration", 0),
        }
        if not effect["target"] or not effect["status"]:
            return
        if effect["duration"] < 0:
            return

        status_log = state.setdefault("status_effects", [])
        status_log.append(effect)

    def _update_metrics(
        self,
        state: Dict[str, Any],
        player_choice: Dict[str, Any],
        applied_flags: Iterable[str],
    ) -> None:
        metrics = state.setdefault(
            "metrics",
            {
                "risk_applied_total": 0,
                "major_flag_set": False,
                "major_events_triggered": 0,
                "major_event_last_turn": None,
            },
        )

        metrics.setdefault("major_events_triggered", 0)
        metrics.setdefault("major_event_last_turn", None)
        metrics.setdefault("major_flag_set", False)

        if player_choice.get("action_type") == "risk":
            metrics["risk_applied_total"] = (
                metrics.get(
                    "risk_applied_total",
                    0,
                )
                + 1
            )

        major_flags = [flag for flag in applied_flags if flag.startswith("major_")]
        if major_flags:
            metrics["major_flag_set"] = True
            metrics["major_events_triggered"] = metrics.get(
                "major_events_triggered",
                0,
            ) + len(major_flags)
            metrics["major_event_last_turn"] = state.get("turn", 0)
