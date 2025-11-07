"""Deterministic rule processing for character-driven world updates."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

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
        seed: Optional[int] = None,
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
            judge_penalties = self._validate_tier_two(
                events, world_context, scene, player_choice, state, seed
            )
            LOGGER.info(
                "Tier two validation passed with penalties: %s", judge_penalties
            )
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
                self._apply_metric_changes(new_state, effects.get("metric_changes"))
            self._update_metrics(new_state, player_choice, applied_flags)
            # Apply judge penalties to metrics
            metrics = new_state.setdefault("metrics", {})
            metrics["glitch"] = max(
                0, metrics.get("glitch", 0) + judge_penalties.get("glitch_penalty", 0)
            )
            metrics["morale"] = max(
                0, metrics.get("morale", 0) - judge_penalties.get("morale_penalty", 0)
            )
            metrics["resources"] = max(
                0,
                metrics.get("resources", 0)
                - judge_penalties.get("resources_penalty", 0),
            )
            metrics["corruption"] = max(
                0,
                metrics.get("corruption", 0)
                + judge_penalties.get("corruption_penalty", 0),
            )
            metrics["order"] = max(
                0, metrics.get("order", 0) - judge_penalties.get("order_penalty", 0)
            )
            LOGGER.info("Judge penalties applied: %s", judge_penalties)
            # --- FEEDBACK SUMMARY LAYER ---
            summary_parts = []
            # Metric deltas overview
            try:
                prev_metrics = state.get("metrics", {})
                after = new_state.get("metrics", {})
                def _delta(m):
                    return int(after.get(m, 0)) - int(prev_metrics.get(m, 0))
                deltas = {m: _delta(m) for m in ("morale", "order", "resources", "knowledge", "glitch")}
                if deltas["morale"] >= 2:
                    summary_parts.append("A spark of hope lifts the garrison.")
                if deltas["morale"] <= -2:
                    summary_parts.append("Anxieties spread among the defenders.")
                if deltas["order"] >= 2:
                    summary_parts.append("Discipline tightens along the walls.")
                if deltas["order"] <= -2:
                    summary_parts.append("Order slips in the confusion.")
                if deltas["resources"] <= -2:
                    summary_parts.append("Supplies are strained.")
                if deltas["knowledge"] >= 2:
                    summary_parts.append("Clues and insights accumulate.")
            except Exception:
                pass
            # Metrik değişimlerini ve önemli olayları özetle
            if judge_penalties.get("glitch_penalty", 0) > 0:
                summary_parts.append("A system glitch ripples through the world.")
            if judge_penalties.get("morale_penalty", 0) > 0:
                summary_parts.append("Morale drops among the villagers.")
            if judge_penalties.get("order_penalty", 0) > 0:
                summary_parts.append("Order falters in the chaos.")
            if judge_penalties.get("corruption_penalty", 0) > 0:
                summary_parts.append("Corruption seeps deeper.")
            if judge_penalties.get("resources_penalty", 0) > 0:
                summary_parts.append("Resources dwindle.")
            # Major event özeti
            metrics = new_state.get("metrics", {})
            if metrics.get("major_flag_set"):
                summary_parts.append("A major event shakes the village.")
            if metrics.get("glitch", 0) > state.get("metrics", {}).get("glitch", 0):
                summary_parts.append("Glitch level rises.")
            if not summary_parts:
                # Deterministic quiet-day variants to reduce repetition
                turn_num = 0
                try:
                    turn_num = int(state.get("turn", 0))
                except Exception:
                    turn_num = 0
                quiet_variants = [
                    "A routine day settles over Lornhaven.",
                    "Little stirs; watch posts rotate without incident.",
                    "Whispers fade and the walls hold steady.",
                    "Calm returns as the sun arcs overhead.",
                    "Another uneventful watch passes by.",
                ]
                summary_parts.append(quiet_variants[turn_num % len(quiet_variants)])
            new_state["summary_text"] = " ".join(summary_parts)
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
            if trust_delta is not None and not isinstance(trust_delta, (int, float)):
                raise TierOneValidationError(
                    f"Invalid trust_delta for '{entry['name']}': {trust_delta}"
                )

            metric_changes = effects.get("metric_changes")
            if metric_changes is not None:
                if not isinstance(metric_changes, dict):
                    raise TierOneValidationError(
                        f"metric_changes for {entry['name']} must be an object"
                    )
                for key, value in metric_changes.items():
                    if not isinstance(value, (int, float)):
                        raise TierOneValidationError(
                            f"metric_changes value for {key} must be number"
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
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
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

        # Accumulate penalties from all judge verdicts
        total_penalties = {
            "glitch_penalty": 0,
            "morale_penalty": 0,
            "resources_penalty": 0,
            "corruption_penalty": 0,
            "order_penalty": 0,
        }

        for entry in events:
            summary = self._build_judge_summary(entry, scene, choice_summary)
            try:
                judge_context = {
                    "WORLD_CONTEXT": world_context,
                    "content": summary,
                }
                # Motif/intent repetition detection
                repetition_count = 0
                motif_repetition = False
                intent_repetition = False
                if state:
                    memory_layers = state.get("memory_layers", []) or []
                    try:
                        repetition_count = sum(
                            1
                            for m in memory_layers
                            if isinstance(m, str)
                            and scene.strip()
                            and scene.strip() in m
                        )
                        # Motif repetition: motif son 3 turda aynıysa
                        motifs = state.get("recent_motifs", [])
                        if isinstance(motifs, str):
                            motifs = [motifs]
                        if len(motifs) >= 3 and len(set(motifs[-3:])) == 1:
                            motif_repetition = True
                        # Intent repetition: intent son 3 turda aynıysa
                        intents = [e.get("intent") for e in events if e.get("intent")]
                        if len(intents) >= 3 and len(set(intents[-3:])) == 1:
                            intent_repetition = True
                    except Exception:
                        repetition_count = 0
                if repetition_count >= 3 or motif_repetition or intent_repetition:
                    judge_context["repetition_count"] = repetition_count
                    judge_context["motif_repetition"] = motif_repetition
                    judge_context["intent_repetition"] = intent_repetition
                    LOGGER.info(
                        "Detected repetition (scene: %d, motif: %s, intent: %s) - informing Judge",
                        repetition_count,
                        motif_repetition,
                        intent_repetition,
                    )
                if flags:
                    judge_context["flags"] = flags
                if status_effects:
                    judge_context["status_effects"] = status_effects
                # Pass tolerance to JudgeAgent if supported
                if hasattr(self.judge_agent, "tolerance"):
                    self.judge_agent.tolerance = self.tolerance
                verdict = self.judge_agent.evaluate(judge_context, seed=seed)
            except AgentError as exc:  # pragma: no cover - defensive
                raise TierTwoValidationError(f"Judge call failed: {exc}") from exc

            LOGGER.debug(
                "Judge verdict for %s: %s",
                entry.get("name"),
                verdict,
            )

            # Apply penalties based on judge verdict
            penalty_level = verdict.get("penalty", "none")
            if penalty_level == "mild":
                total_penalties["glitch_penalty"] += 5
                total_penalties["morale_penalty"] += 5
            elif penalty_level == "medium":
                total_penalties["glitch_penalty"] += 10
                total_penalties["morale_penalty"] += 10
                total_penalties["resources_penalty"] += 5
            elif penalty_level == "severe":
                total_penalties["glitch_penalty"] += 15
                total_penalties["morale_penalty"] += 15
                total_penalties["corruption_penalty"] += 10
                # Severe penalties can also cause rejection
                if (
                    verdict.get("coherence", 100) < 30
                    or verdict.get("integrity", 100) < 30
                ):
                    reason = verdict.get("reason", "severe narrative violation")
                    raise TierTwoValidationError(
                        f"Judge rejected update for '{entry['name']}': {reason}"
                    )

            if not verdict.get("consistent", True):
                reason = verdict.get("reason", "unknown reason")
                raise TierTwoValidationError(
                    f"Judge rejected update for '{entry['name']}': {reason}"
                )

            # Incorporate structured penalty magnitudes directly into totals
            # Mapping: positive magnitudes increase corresponding *_penalty buckets
            magnitudes = verdict.get("penalty_magnitude", {}) or {}
            try:
                morale_delta = magnitudes.get("morale")
                if isinstance(morale_delta, (int, float)) and morale_delta < 0:
                    total_penalties["morale_penalty"] += int(abs(morale_delta))
                glitch_delta = magnitudes.get("glitch")
                if isinstance(glitch_delta, (int, float)) and glitch_delta > 0:
                    total_penalties["glitch_penalty"] += int(glitch_delta)
                resources_delta = magnitudes.get("resources")
                if isinstance(resources_delta, (int, float)) and resources_delta < 0:
                    total_penalties["resources_penalty"] += int(abs(resources_delta))
                corruption_delta = magnitudes.get("corruption")
                if isinstance(corruption_delta, (int, float)) and corruption_delta > 0:
                    total_penalties["corruption_penalty"] += int(corruption_delta)
                order_delta = magnitudes.get("order")
                if isinstance(order_delta, (int, float)) and order_delta < 0:
                    total_penalties["order_penalty"] += int(abs(order_delta))
            except Exception:
                # Be defensive; do not break pipeline on malformed magnitudes
                pass

        return total_penalties

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
            new_trust = _clamp(
                current + int(trust_delta),
                self.trust_floor,
                self.trust_ceiling,
            )
            trust[character_name] = new_trust
            LOGGER.info(
                "Trust updated for %s: %s -> %s (delta: %s)",
                character_name,
                current,
                new_trust,
                trust_delta,
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

    def _apply_metric_changes(self, state: Dict[str, Any], changes: Any) -> None:
        if not isinstance(changes, dict):
            return
        metrics = state.setdefault("metrics", {})
        for key, delta in changes.items():
            if isinstance(delta, (int, float)):
                current = metrics.get(key, 0)
                metrics[key] = max(0, current + delta)

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

    def tick_status_effects(self, state: Dict[str, Any]) -> None:
        """Decrement duration of all status effects and remove expired ones."""
        status_effects = state.get("status_effects", [])
        updated_effects = []
        for effect in status_effects:
            duration = effect.get("duration", 0) - 1
            if duration > 0:
                effect["duration"] = duration
                updated_effects.append(effect)
        state["status_effects"] = updated_effects
        LOGGER.debug("Status effects ticked: %s", updated_effects)

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
        # Use set-based deduplication: convert to tuple for uniqueness
        effect_tuple = (effect["target"], effect["status"], effect["duration"])
        status_set = set()
        for existing in status_log:
            existing_tuple = (
                existing.get("target"),
                existing.get("status"),
                existing.get("duration"),
            )
            status_set.add(existing_tuple)
        if effect_tuple not in status_set:
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

        # Track player choice history for repetitive behavior detection
        choice_history = state.setdefault("player_choice_history", [])
        choice_type = player_choice.get("action_type", "unknown")
        choice_history.append(choice_type)
        if len(choice_history) > 10:
            choice_history.pop(0)
        state["player_choice_history"] = choice_history

        # If player chose 'observe' 3 times in a row, trigger world variation
        observe_count = sum(
            1 for c in choice_history[-3:] if c in ["observation", "observe"]
        )
        if observe_count >= 3:
            LOGGER.info("Player observed 3 times in a row, triggering world variation")
            flags = state.setdefault("flags", [])
            if "force_world_variation" not in flags:
                flags.append("force_world_variation")
            metrics["morale"] = max(0, metrics.get("morale", 0) - 2)

        # Choice impact mapping: apply small, deterministic effects per action type
        try:
            impact_map = {
                "dialogue": [("knowledge", 1)],
                "exploration": [("knowledge", 1), ("resources", 1)],
                "observation": [("knowledge", 1)],
                "preparation": [("order", 1)],
                "risk": [("glitch", 2), ("corruption", 1)],
                "trade": [("resources", 2), ("morale", 1)],
                "emergency": [("order", 2), ("morale", -1)],
            }
            action_type = str(player_choice.get("action_type", "")).lower()
            for metric_key, delta in impact_map.get(action_type, []):
                current = metrics.get(metric_key, 0)
                metrics[metric_key] = max(0, int(current) + int(delta))
                LOGGER.info(
                    "Choice impact applied: %s %+d (action_type=%s)",
                    metric_key,
                    delta,
                    action_type,
                )
        except Exception:
            # Defensive; do not break flow if mapping fails
            pass

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
            # --- GLITCH METRIC ESCALATION ---
            import random

            glitch_increase = random.randint(1, 3)
            metrics["glitch"] = max(0, metrics.get("glitch", 0) + glitch_increase)
            LOGGER.info(f"Major event: glitch increased by {glitch_increase}")

        # Major event starvation protection: if no major event for >5 turns,
        # force a major event flag so EventAgent will create one.
        try:
            current_turn = int(state.get("turn", 0))
            last_turn = metrics.get("major_event_last_turn")
            if last_turn is not None and isinstance(last_turn, int):
                if current_turn - last_turn > 5:
                    flags = state.setdefault("flags", [])
                    if "force_major_event" not in flags:
                        flags.append("force_major_event")
                        metrics["morale"] = max(0, metrics.get("morale", 0) - 1)
                        LOGGER.info(
                            "Major event starvation detected (last=%s, now=%s); forcing major event",
                            last_turn,
                            current_turn,
                        )
            # Diversity-based organic major event trigger: if recent motifs are too similar,
            # nudge the system to create a major event without always forcing it.
            recent_motifs = state.get("recent_motifs", [])
            if isinstance(recent_motifs, list) and len(recent_motifs) >= 4:
                window = [str(m) for m in recent_motifs[-4:]]
                diversity = len(set(window))
                if diversity <= 2:
                    flags = state.setdefault("flags", [])
                    if "force_major_event" not in flags and current_turn % 3 == 1:
                        flags.append("force_major_event")
                        LOGGER.info(
                            "Low motif diversity detected (%s), hinting major event",
                            window,
                        )
        except Exception:
            # Be defensive; do not break game flow on bookkeeping errors
            LOGGER.debug("Failed to evaluate major event starvation check")

        # Update relationship summary based on trust changes
        self._update_relationship_summary(state)

    def _update_relationship_summary(self, state: Dict[str, Any]) -> None:
        """Update relationship summary based on current NPC trust levels."""
        npc_trust = state.get("npc_trust", {})
        if not npc_trust:
            return

        summaries = []
        for npc_name, trust_level in npc_trust.items():
            if trust_level >= 2:
                status = "trusts the player deeply"
            elif trust_level >= 1:
                status = "trusts the player"
            elif trust_level == 0:
                status = "is neutral toward the player"
            elif trust_level >= -1:
                status = "distrusts the player"
            else:
                status = "deeply distrusts the player"
            summaries.append(f"{npc_name} {status}")

        if summaries:
            relationship_summary = "; ".join(summaries)
            state["relationship_summary"] = relationship_summary
            LOGGER.info("Relationship summary updated: %s", relationship_summary)

    def apply_environmental_effects(
        self, state: Dict[str, Any], seed: Optional[int] = None
    ) -> None:
        """Apply deterministic environmental effects like weather and NPC drift."""
        import random

        rng = random.Random(seed) if seed is not None else random.Random()

        weather = state.get("weather", {})
        if weather.get("type") == "rain":
            # Apply wetness to items
            items = state.get("items", {})
            for item_id, item in items.items():
                wetness = item.get("wetness", 0.0)
                wetness += rng.uniform(0.1, 0.3)  # Deterministic increase
                item["wetness"] = min(wetness, 1.0)
                durability = item.get("durability", 1.0)
                if wetness > 0.5 and durability > 0.1:
                    durability -= rng.uniform(0.01, 0.05)
                    item["durability"] = max(durability, 0.0)
                item["last_soaked_turn"] = state.get("turn", 0)

            # Update NPC memory and mood
            npc_memory = state.get("npc_memory", {})
            for npc_id, memory in npc_memory.items():
                memory["last_seen_weather"] = weather
                recent_events = memory.get("recent_events", [])
                recent_events.append(
                    {"turn": state.get("turn", 0), "desc": "Rain affected the area"}
                )
                memory["recent_events"] = recent_events[-5:]  # Keep last 5
                mood = memory.get("mood", {})
                morale_delta = mood.get("morale_delta", 0.0)
                morale_delta -= rng.uniform(0.1, 0.5)  # Rain lowers morale
                mood["morale_delta"] = morale_delta
                memory["mood"] = mood

            # Update global metrics
            metrics = state.get("metrics", {})
            morale = metrics.get("morale", 0.0)
            morale -= rng.uniform(1, 3)
            metrics["morale"] = max(morale, -100)
            supplies = metrics.get("supplies", 0.0)
            supplies -= rng.uniform(0.5, 1.5)  # Rain affects supplies
            metrics["supplies"] = max(supplies, 0)
            state["metrics"] = metrics

        # NPC drift: small random changes
        npc_memory = state.get("npc_memory", {})
        for npc_id, memory in npc_memory.items():
            mood = memory.get("mood", {})
            morale_delta = mood.get("morale_delta", 0.0)
            morale_delta += rng.uniform(-0.2, 0.2)  # Small drift
            mood["morale_delta"] = morale_delta
            memory["mood"] = mood

        LOGGER.info("Environmental effects applied with seed %s", seed)

    def evaluate_win_loss(
        self, state: Dict[str, Any], turn_number: int
    ) -> Dict[str, Any]:
        """Evaluate win/loss conditions based on current game state.

        Args:
            state: Current game state
            turn_number: Current turn number

        Returns:
            Dict with 'status' ('ongoing', 'win', 'loss') and 'reason'
        """
        metrics = state.get("metrics", {})

        # Extract key metrics
        morale = metrics.get("morale", 50)
        resources = metrics.get("resources", 40)
        order = metrics.get("order", 50)
        corruption = metrics.get("corruption", 10)
        glitch = metrics.get("glitch", 0)

        # Victory conditions
        if turn_number >= 15 and morale >= 60 and order >= 70:
            return {
                "status": "win",
                "reason": "survived_15_turns_high_morale",
                "description": "15 tur savunma başarısı!",
            }

        # Harmony (soft) — earlier achievable than perfect harmony
        if morale >= 60 and corruption < 5 and order >= 50:
            return {
                "status": "win",
                "reason": "harmony_restored",
                "description": "Uyum yeniden sağlandı!",
            }

        if morale >= 80 and corruption <= 5:
            return {
                "status": "win",
                "reason": "perfect_harmony",
                "description": "Mükemmel uyum!",
            }

        # Additional victories to diversify endings
        if metrics.get("knowledge", 0) >= 75 and glitch <= 20:
            return {
                "status": "win",
                "reason": "insight_win",
                "description": "Bilgi, kaosu yendi.",
            }

        if resources <= 5 and order >= 60 and glitch <= 40:
            return {
                "status": "win",
                "reason": "sacrifice_win",
                "description": "Bedel ödendi; köy ayakta kaldı.",
            }

        # Defeat conditions
        if morale <= 10:
            return {
                "status": "loss",
                "reason": "morale_crash",
                "description": "Moral çöktü!",
            }

        if resources <= 5:
            return {
                "status": "loss",
                "reason": "resources_depleted",
                "description": "Kaynaklar tükendi!",
            }

        if order <= 20:
            return {
                "status": "loss",
                "reason": "chaos_overwhelms",
                "description": "Kaos hakim!",
            }

        if glitch >= 80:
            return {
                "status": "loss",
                "reason": "system_glitch",
                "description": "Sistem hatası!",
            }

        # Additional losses before timer checks
        if order <= 15 and glitch >= 50:
            return {
                "status": "loss",
                "reason": "breach_loss",
                "description": "Surlar çöktü; düzen dağıldı.",
            }

        if morale <= 20 and corruption >= 40 and order <= 30:
            return {
                "status": "loss",
                "reason": "mutiny_loss",
                "description": "İçeride isyan patladı.",
            }

        if turn_number >= 20:
            return {
                "status": "loss",
                "reason": "turn_limit_exceeded",
                "description": "20 tur limit aşıldı!",
            }

        # Check for major defeat events
        major_events = metrics.get("major_events_triggered", 0)
        if major_events >= 3 and morale <= 30:
            return {
                "status": "loss",
                "reason": "major_events_overwhelm",
                "description": "Çok fazla olay!",
            }

        return {
            "status": "ongoing",
            "reason": "conditions_not_met",
            "description": "Oyun devam ediyor...",
        }
