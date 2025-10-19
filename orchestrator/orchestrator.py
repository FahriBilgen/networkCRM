"""Deterministic orchestrator coordinating Fortress Director agents."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from fortress_director.agents.character_agent import CharacterAgent
from fortress_director.agents.event_agent import EventAgent
from fortress_director.agents.judge_agent import JudgeAgent
from fortress_director.agents.world_agent import WorldAgent
from fortress_director.settings import SETTINGS
from fortress_director.rules.rules_engine import (
    RulesEngine,
    TierTwoValidationError,
)
from fortress_director.codeaware.function_registry import (
    FunctionCall,
    FunctionValidationError,
    SafeFunctionRegistry,
    Validator,
)
from fortress_director.codeaware.function_validator import (
    FunctionCallValidator,
)
from fortress_director.codeaware.rollback_system import RollbackSystem
from fortress_director.utils.output_validator import validate_turn_output


LOGGER = logging.getLogger(__name__)


SENSORY_DETAILS_DEFAULT = "Drums thud beyond the walls while the wind carries grit."

RELATIONSHIP_SUMMARY_DEFAULT = "Rhea trusts the player; Boris weighs every trade."


DEFAULT_WORLD_STATE: Dict[str, Any] = {
    "turn": 0,
    "day": 1,
    "time": "dawn",
    "current_room": "lornhaven_wall",
    "recent_events": [],
    "recent_motifs": [],
    "recent_major_events": [],
    "world_constraint_from_prev_turn": {
        "atmosphere": "low clouds hug the battlements",
        "sensory_details": SENSORY_DETAILS_DEFAULT,
    },
    "player": {
        "name": "The Shieldbearer",
        "inventory": ["oil lamp", "patched shield"],
        "stats": {"resolve": 3, "empathy": 2},
        "summary": "A weary defender holding the western wall.",
    },
    "character_summary": (
        "Rhea is loyal but impulsive; Boris is cautious and calculating."
    ),
    "relationship_summary": RELATIONSHIP_SUMMARY_DEFAULT,
    "metrics": {
        "risk_applied_total": 0,
        "major_flag_set": False,
        "major_events_triggered": 0,
        "major_event_last_turn": None,
    },
}


class StateStore:
    """Lightweight JSON-backed state store."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._state = self._load()

    def snapshot(self) -> Dict[str, Any]:
        """Return a deep copy of the current state for safe mutation."""

        snapshot = deepcopy(self._state)
        LOGGER.debug(
            "State snapshot loaded from %s (turn=%s)",
            self._path,
            snapshot.get("turn"),
        )
        return snapshot

    def persist(self, state: Dict[str, Any]) -> None:
        """Replace current state with provided snapshot and flush to disk."""

        self._state = deepcopy(state)
        payload = json.dumps(self._state, indent=2)
        self._path.write_text(payload, encoding="utf-8")
        LOGGER.debug(
            "State persisted to %s (turn=%s)",
            self._path,
            state.get("turn"),
        )

    def _load(self) -> Dict[str, Any]:
        if not self._path.exists():
            return deepcopy(DEFAULT_WORLD_STATE)
        text = self._path.read_text(encoding="utf-8").strip()
        if not text:
            LOGGER.debug(
                "World state file %s empty; loading defaults",
                self._path,
            )
            return deepcopy(DEFAULT_WORLD_STATE)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            LOGGER.warning(
                "World state file %s corrupt; loading defaults",
                self._path,
            )
            return deepcopy(DEFAULT_WORLD_STATE)

    def summary(self) -> Dict[str, Any]:
        """Provide a user-facing snapshot for CLI debug output."""

        state = self._state
        return {
            "turn": state.get("turn"),
            "day": state.get("day"),
            "time": state.get("time"),
            "current_room": state.get("current_room"),
            "recent_events": state.get("recent_events", [])[-3:],
            "recent_motifs": state.get("recent_motifs", [])[-3:],
        }


@dataclass
class Orchestrator:
    """Coordinates the serialized flow of the entire game turn."""

    state_store: StateStore
    event_agent: EventAgent
    world_agent: WorldAgent
    character_agent: CharacterAgent
    judge_agent: JudgeAgent
    rules_engine: RulesEngine
    function_registry: SafeFunctionRegistry
    function_validator: FunctionCallValidator
    rollback_system: RollbackSystem

    @classmethod
    def build_default(cls) -> "Orchestrator":
        """Factory that wires default dependencies."""
        state_store = StateStore(SETTINGS.world_state_path)
        judge_agent = JudgeAgent()
        tolerance = 1  # Default: allow small reintroductions of existing mysteries
        registry = SafeFunctionRegistry()
        validator = FunctionCallValidator(
            registry,
            max_calls_per_function=5,
            max_total_calls=20,
        )
        rollback_system = RollbackSystem(
            snapshot_provider=state_store.snapshot,
            restore_callback=state_store.persist,
            max_checkpoints=3,
            logger=LOGGER,
        )
        orchestrator = cls(
            state_store=state_store,
            event_agent=EventAgent(),
            world_agent=WorldAgent(),
            character_agent=CharacterAgent(),
            judge_agent=judge_agent,
            rules_engine=RulesEngine(judge_agent=judge_agent, tolerance=tolerance),
            function_registry=registry,
            function_validator=validator,
            rollback_system=rollback_system,
        )
        orchestrator._register_default_safe_functions()
        return orchestrator

    def run_turn(
        self,
        *,
        player_choice_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a full deterministic turn and persist the new state. Logs every step in detail."""
        LOGGER.info("run_turn called (player_choice_id=%s)", player_choice_id)

        checkpoint_metadata = {"phase": "turn_start"}
        if player_choice_id:
            checkpoint_metadata["player_choice_id"] = player_choice_id
        LOGGER.debug(
            "Resetting function validator and creating checkpoint: %s",
            checkpoint_metadata,
        )
        self.function_validator.reset()
        self.rollback_system.create_checkpoint(metadata=checkpoint_metadata)

        try:
            LOGGER.info("Turn execution started.")
            state_snapshot = self.state_store.snapshot()
            LOGGER.debug(
                "Pre-turn state snapshot: %s",
                self._stringify(state_snapshot),
            )
            world_context = self._build_world_context(state_snapshot)
            LOGGER.info("World context built.")
            LOGGER.debug("World context payload: %s", world_context)
            LOGGER.info(
                "Starting turn %s in room %s",
                state_snapshot.get("turn", 0),
                state_snapshot.get("current_room", "unknown"),
            )

            world_request = {
                "WORLD_CONTEXT": world_context,
                "room": state_snapshot.get("current_room", "unknown"),
            }
            LOGGER.debug(
                "World agent input: %s",
                self._stringify(world_request),
            )
            LOGGER.info("Calling world_agent.describe...")
            world_output = self.world_agent.describe(world_request)
            LOGGER.info("World agent returned output.")
            LOGGER.debug(
                "World agent output: %s",
                self._stringify(world_output),
            )

            recent_motifs_text = (
                ", ".join(state_snapshot.get("recent_motifs", [])) or "none"
            )
            event_request = {
                "WORLD_CONTEXT": world_context,
                "day": state_snapshot.get("day", 1),
                "time": state_snapshot.get("time", "dawn"),
                "room": state_snapshot.get("current_room", "unknown"),
                "recent_events": self._format_recent_events(state_snapshot),
                "world_constraint_from_prev_turn": json.dumps(
                    state_snapshot.get("world_constraint_from_prev_turn", {})
                ),
                "recent_motifs": recent_motifs_text,
                # lore_continuity_weight: Kaç büyük olay tetiklendi?
                "lore_continuity_weight": state_snapshot.get("metrics", {}).get(
                    "major_events_triggered", 0
                ),
            }
            LOGGER.debug(
                "Event agent input: %s",
                self._stringify(event_request),
            )
            LOGGER.info("Calling event_agent.generate...")
            event_output = self.event_agent.generate(event_request)
            LOGGER.info("Event agent returned output.")
            LOGGER.debug(
                "Event agent output: %s",
                self._stringify(event_output),
            )

            LOGGER.info("Resolving player choice...")
            chosen_option = self._resolve_player_choice(
                event_output,
                player_choice_id,
            )
            LOGGER.info("Player choice resolved: %s", chosen_option)
            LOGGER.debug(
                "Player choice resolved: %s",
                self._stringify(chosen_option),
            )

            character_request = {
                "WORLD_CONTEXT": world_context,
                "scene_short": event_output.get("scene", ""),
                "player_choice": chosen_option.get("text", ""),
                "atmosphere": world_output.get("atmosphere", ""),
                "sensory_details": world_output.get("sensory_details", ""),
                "char_brief": state_snapshot.get("character_summary", ""),
                "relationship_summary_from_state": state_snapshot.get(
                    "relationship_summary", ""
                ),
                "player_inventory_brief": ", ".join(
                    state_snapshot["player"].get("inventory", [])
                ),
            }
            LOGGER.debug(
                "Character agent input: %s",
                self._stringify(character_request),
            )
            LOGGER.info("Calling character_agent.react...")
            character_output = self.character_agent.react(character_request)
            LOGGER.info("Character agent returned output.")
            LOGGER.debug(
                "Character agent output: %s",
                self._stringify(character_output),
            )

            LOGGER.info("Injecting major event effect...")
            major_event_effect = self._inject_major_event_effect(
                state_snapshot,
                event_output,
                character_output,
            )
            LOGGER.info("Major event effect injected.")
            if major_event_effect:
                LOGGER.debug(
                    "Major event effect applied: %s",
                    self._stringify(major_event_effect),
                )
            major_event_summary = (
                self._format_major_event_summary(major_event_effect)
                if major_event_effect
                else None
            )

            warnings: List[str] = []
            try:
                LOGGER.info("Submitting reactions to rules engine...")
                LOGGER.debug(
                    "Submitting reactions to rules engine: %s",
                    self._stringify(character_output),
                )
                state = self.rules_engine.process(
                    state=state_snapshot,
                    character_events=character_output,
                    world_context=world_context,
                    scene=event_output.get("scene", ""),
                    player_choice=chosen_option,
                )
                LOGGER.info(
                    "Rules engine accepted updates (turn=%s)",
                    state_snapshot.get("turn", 0) + 1,
                )
            except TierTwoValidationError as exc:
                LOGGER.warning("Judge vetoed character updates: %s", exc)
                warnings.append(str(exc))
                fallback = self._build_fallback_reaction(
                    state_snapshot,
                    chosen_option,
                )
                character_output = [fallback]
                fallback_note = "Applied fallback defensive stance for primary NPC."
                warnings.append(fallback_note)
                LOGGER.info(fallback_note)
                state = state_snapshot
                major_event_effect = self._inject_major_event_effect(
                    state_snapshot,
                    event_output,
                    character_output,
                )
                if major_event_effect:
                    LOGGER.debug(
                        "Major event effect after fallback: %s",
                        self._stringify(major_event_effect),
                    )
                major_event_summary = (
                    self._format_major_event_summary(major_event_effect)
                    if major_event_effect
                    else None
                )

            LOGGER.info("Updating state and persisting...")
            self._update_state(
                state,
                world_output,
                event_output,
                chosen_option,
            )
            LOGGER.debug(
                "State after update: %s",
                self._stringify(state),
            )
            self.state_store.persist(state)
            LOGGER.info("Executing safe function queue...")
            safe_function_results = self._execute_safe_function_queue(
                event_output=event_output,
                character_output=character_output,
            )
            LOGGER.info("Safe function queue executed.")

            result = {
                "world": world_output,
                "event": event_output,
                "player_choice": chosen_option,
                "character_reactions": character_output,
            }
            LOGGER.info("Turn result built.")
            if major_event_effect:
                result["major_event_effect"] = major_event_effect
            if major_event_summary:
                result["major_event_effect_summary"] = major_event_summary
            if warnings:
                result["warnings"] = warnings
            if safe_function_results:
                result["safe_function_results"] = safe_function_results
            LOGGER.debug(
                "Turn result before validation: %s",
                self._stringify(result),
            )
            validate_turn_output(result)
            LOGGER.info("Turn output validated successfully.")
        except Exception as exc:
            class_name = exc.__class__.__name__
            rollback_reason = f"Turn execution failed: {class_name}"
            LOGGER.error("Exception during turn: %s", exc, exc_info=True)
            try:
                self.rollback_system.rollback(reason=rollback_reason)
                LOGGER.info("Rollback performed after exception.")
            except Exception as rollback_error:  # pragma: no cover - defensive
                LOGGER.error(
                    "Rollback failed after %s: %s",
                    exc.__class__.__name__,
                    rollback_error,
                )
            raise
        else:
            self.rollback_system.clear()
            LOGGER.info("Turn completed successfully.")
            return result

    def register_safe_function(
        self,
        name: str,
        function: Callable[..., Any],
        *,
        validator: Validator | None = None,
    ) -> None:
        """Register a safe function available to deterministic agents."""

        self.function_registry.register(name, function, validator=validator)

    def run_safe_function(
        self,
        payload: Dict[str, Any],
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a safe function with validation and rollback support."""

        return self.rollback_system.run_validated_call(
            self.function_validator,
            payload,
            metadata=metadata,
        )

    def _register_default_safe_functions(self) -> None:
        """Register baseline safe functions used by the scenario."""

        self.register_safe_function(
            "change_weather",
            self._safe_change_weather,
            validator=self._validate_change_weather_call,
        )
        self.register_safe_function(
            "spawn_item",
            self._safe_spawn_item,
            validator=self._validate_spawn_item_call,
        )
        self.register_safe_function(
            "move_npc",
            self._safe_move_npc,
            validator=self._validate_move_npc_call,
        )

    def _validate_change_weather_call(
        self,
        call: FunctionCall,
    ) -> FunctionCall:
        if call.args:
            raise FunctionValidationError(
                "change_weather does not accept positional arguments",
            )
        kwargs = dict(call.kwargs)
        atmosphere = kwargs.get("atmosphere")
        details = kwargs.get("sensory_details")
        if not isinstance(atmosphere, str) or not atmosphere.strip():
            raise FunctionValidationError(
                "change_weather requires a non-empty 'atmosphere' string",
            )
        if not isinstance(details, str) or not details.strip():
            raise FunctionValidationError(
                "change_weather requires non-empty 'sensory_details'",
            )
        sanitized = {
            "atmosphere": atmosphere.strip(),
            "sensory_details": details.strip(),
        }
        return FunctionCall(
            name=call.name,
            args=(),
            kwargs=sanitized,
            metadata=call.metadata,
        )

    def _validate_spawn_item_call(
        self,
        call: FunctionCall,
    ) -> FunctionCall:
        if call.args:
            raise FunctionValidationError(
                "spawn_item does not accept positional arguments",
            )
        kwargs = dict(call.kwargs)
        item_id = kwargs.get("item_id")
        target = kwargs.get("target", "player")
        if not isinstance(item_id, str) or not item_id.strip():
            raise FunctionValidationError(
                "spawn_item requires a non-empty 'item_id' string",
            )
        if not isinstance(target, str) or not target.strip():
            raise FunctionValidationError(
                "spawn_item requires a non-empty 'target' string",
            )
        sanitized = {
            "item_id": item_id.strip(),
            "target": target.strip(),
        }
        return FunctionCall(
            name=call.name,
            args=(),
            kwargs=sanitized,
            metadata=call.metadata,
        )

    def _validate_move_npc_call(
        self,
        call: FunctionCall,
    ) -> FunctionCall:
        if call.args:
            raise FunctionValidationError(
                "move_npc does not accept positional arguments",
            )
        kwargs = dict(call.kwargs)
        npc_id = kwargs.get("npc_id")
        location = kwargs.get("location")
        if not isinstance(npc_id, str) or not npc_id.strip():
            raise FunctionValidationError(
                "move_npc requires a non-empty 'npc_id' string",
            )
        if not isinstance(location, str) or not location.strip():
            raise FunctionValidationError(
                "move_npc requires a non-empty 'location' string",
            )
        sanitized = {
            "npc_id": npc_id.strip(),
            "location": location.strip(),
        }
        return FunctionCall(
            name=call.name,
            args=(),
            kwargs=sanitized,
            metadata=call.metadata,
        )

    def _safe_change_weather(
        self,
        *,
        atmosphere: str,
        sensory_details: str,
    ) -> Dict[str, str]:
        state = self.state_store.snapshot()
        payload = state.setdefault("world_constraint_from_prev_turn", {})
        payload["atmosphere"] = atmosphere
        payload["sensory_details"] = sensory_details
        self.state_store.persist(state)
        return {
            "atmosphere": payload["atmosphere"],
            "sensory_details": payload["sensory_details"],
        }

    def _safe_spawn_item(
        self,
        *,
        item_id: str,
        target: str,
    ) -> Dict[str, Any]:
        state = self.state_store.snapshot()
        if target == "player":
            player = state.setdefault("player", {})
            inventory = player.setdefault("inventory", [])
            if item_id not in inventory:
                inventory.append(item_id)
            result = {
                "target": "player",
                "inventory": list(inventory),
            }
        else:
            storage = state.setdefault("items", {})
            bucket = storage.setdefault(target, [])
            if item_id not in bucket:
                bucket.append(item_id)
            result = {
                "target": target,
                "items": list(bucket),
            }
        self.state_store.persist(state)
        return result

    def _safe_move_npc(
        self,
        *,
        npc_id: str,
        location: str,
    ) -> Dict[str, str]:
        state = self.state_store.snapshot()
        registry = state.setdefault("npc_locations", {})
        registry[npc_id] = location
        self.state_store.persist(state)
        return {
            "npc_id": npc_id,
            "location": location,
        }

    def _execute_safe_function_queue(
        self,
        *,
        event_output: Dict[str, Any],
        character_output: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Execute any safe function requests emitted by agents."""

        calls = self._collect_safe_function_calls(
            event_output=event_output,
            character_output=character_output,
        )
        results: List[Dict[str, Any]] = []
        for payload, metadata in calls:
            outcome = self.run_safe_function(payload, metadata=metadata)
            results.append(
                {
                    "name": payload["name"],
                    "result": outcome,
                    "metadata": metadata,
                }
            )
        return results

    def _collect_safe_function_calls(
        self,
        *,
        event_output: Dict[str, Any],
        character_output: List[Dict[str, Any]],
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        queue: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        queue.extend(
            self._normalize_safe_function_entries(
                event_output.get("safe_functions"),
                source="event_agent",
            )
        )
        for reaction in character_output:
            if not isinstance(reaction, dict):
                continue
            reaction_name = reaction.get("name", "unknown")
            if isinstance(reaction_name, str) and reaction_name.strip():
                source_label = f"character:{reaction_name.strip()}"
            else:
                source_label = "character:unknown"
            queue.extend(
                self._normalize_safe_function_entries(
                    reaction.get("safe_functions"),
                    source=source_label,
                )
            )
        return queue

    def _normalize_safe_function_entries(
        self,
        entries: Any,
        *,
        source: str,
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        if not isinstance(entries, list):
            return []
        normalized: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for entry in entries:
            if isinstance(entry, str):
                # Parse string format like "change_weather('overcast')" or "spawn_item('torch', 'lornhaven_wall')"
                try:
                    func_name, arg_str = entry.split("(", 1)
                    func_name = func_name.strip()
                    args = arg_str.strip(")").strip()
                    payload: Dict[str, Any] = {"name": func_name}
                    if func_name == "change_weather":
                        # Assume single arg for weather_type, map to atmosphere
                        arg_value = args.strip("'").strip('"')
                        payload["kwargs"] = {
                            "atmosphere": arg_value,
                            "sensory_details": "The weather shifts subtly.",
                        }
                    elif func_name == "spawn_item":
                        # Parse 'item_name', 'location'
                        parts = [
                            p.strip().strip("'").strip('"') for p in args.split(",")
                        ]
                        if len(parts) == 2:
                            payload["kwargs"] = {
                                "item_id": parts[0],
                                "target": parts[1],
                            }
                        else:
                            raise ValueError("Invalid spawn_item args")
                    elif func_name == "move_npc":
                        # Parse 'npc_name', 'target_room'
                        parts = [
                            p.strip().strip("'").strip('"') for p in args.split(",")
                        ]
                        if len(parts) == 2:
                            payload["kwargs"] = {
                                "npc_name": parts[0],
                                "target_room": parts[1],
                            }
                        else:
                            raise ValueError("Invalid move_npc args")
                    else:
                        payload["kwargs"] = {}
                    metadata: Dict[str, Any] = {"source": source}
                    normalized.append((payload, metadata))
                except Exception as e:
                    LOGGER.warning(f"Failed to parse safe function call: {entry} ({e})")
                    continue
            elif isinstance(entry, dict):
                # Existing dict format
                raw_name = entry.get("name")
                if not isinstance(raw_name, str) or not raw_name.strip():
                    continue
                payload: Dict[str, Any] = {"name": raw_name.strip()}
                if "args" in entry:
                    payload["args"] = entry.get("args")
                if "kwargs" in entry:
                    payload["kwargs"] = entry.get("kwargs")
                entry_metadata = entry.get("metadata")
                payload_metadata: Dict[str, Any] = {}
                if isinstance(entry_metadata, dict):
                    payload_metadata = dict(entry_metadata)
                    payload["metadata"] = payload_metadata
                metadata: Dict[str, Any] = {"source": source}
                metadata.update(payload_metadata)
                normalized.append((payload, metadata))
            else:
                continue
        return normalized

    def _update_state(
        self,
        state: Dict[str, Any],
        world_output: Dict[str, Any],
        event_output: Dict[str, Any],
        chosen_option: Dict[str, Any],
    ) -> None:
        state["turn"] = state.get("turn", 0) + 1
        state["world_constraint_from_prev_turn"] = world_output
        recent_events = state.setdefault("recent_events", [])
        recent_events.append(event_output.get("scene", ""))
        state["recent_events"] = recent_events[-5:]
        recent_motifs = state.setdefault("recent_motifs", [])
        motif = chosen_option.get("action_type")
        if motif:
            recent_motifs.append(motif)
            state["recent_motifs"] = recent_motifs[-5:]
        major_events = state.setdefault("recent_major_events", [])
        major_events.append(bool(event_output.get("major_event")))
        state["recent_major_events"] = major_events[-5:]

    def _resolve_player_choice(
        self,
        event_output: Dict[str, Any],
        player_choice_id: Optional[str],
    ) -> Dict[str, Any]:
        options = event_output.get("options", [])
        if not options:
            return {}
        if player_choice_id:
            for option in options:
                if option.get("id") == player_choice_id:
                    return option
        return options[0]

    def _build_fallback_reaction(
        self,
        state: Dict[str, Any],
        choice: Dict[str, Any],
    ) -> Dict[str, Any]:
        import random

        name = self._infer_primary_npc_name(state)
        action = "hold_position"
        action_desc = choice.get("action_type", "act")
        fallback_templates = [
            f"{name} keeps the western wall secure while you {action_desc}.",
            f"{name} stands guard, watching over the wall as you {action_desc}.",
            f"{name} maintains a defensive stance while you {action_desc}.",
            f"{name} remains vigilant on the wall while you {action_desc}.",
            f"{name} focuses on defense, giving you space to {action_desc}.",
            f"{name} holds position, ensuring the wall is safe as you {action_desc}.",
        ]
        speech = random.choice(fallback_templates)[:200]
        return {
            "name": name,
            "intent": "defend",
            "action": action,
            "speech": speech,
            "effects": {},
        }

    def _inject_major_event_effect(
        self,
        state: Dict[str, Any],
        event_output: Dict[str, Any],
        character_output: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not event_output.get("major_event"):
            return None
        if not character_output:
            return None

        primary = character_output[0]
        effects = primary.get("effects")
        if not isinstance(effects, dict):
            effects = {}
            primary["effects"] = effects

        raw_flags = effects.get("flag_set")
        if isinstance(raw_flags, list):
            flag_set = [str(flag).strip() for flag in raw_flags if str(flag).strip()]
        else:
            flag_set = []
        derived_flag = self._derive_major_event_flag(state)
        if derived_flag not in flag_set:
            flag_set.append(derived_flag)
        effects["flag_set"] = flag_set

        status_change = effects.get("status_change")
        if not isinstance(status_change, dict):
            status_change = {}
        fallback_target = primary.get("name") or "Rhea"
        target = status_change.get("target")
        if (
            not isinstance(target, str)
            or not target.strip()
            or target.strip().lower() in {"string", "unknown"}
        ):
            target = fallback_target
        else:
            target = target.strip()
        status_change["target"] = target
        status_label = status_change.get("status")
        if (
            not isinstance(status_label, str)
            or not status_label.strip()
            or status_label.strip().lower() in {"string", "unknown"}
        ):
            status_change["status"] = "tense_watch"
        else:
            status_change["status"] = status_label.strip()
        duration_raw = status_change.get("duration")
        if not isinstance(duration_raw, int) or duration_raw < 3:
            status_change["duration"] = 3
        effects["status_change"] = status_change

        trust_delta = effects.get("trust_delta")
        if trust_delta not in (-1, 0, 1):
            effects["trust_delta"] = 0

        return {
            "applied_flag": derived_flag,
            "status_change": status_change,
            "applied_to": status_change["target"],
        }

    def _build_world_context(self, state: Dict[str, Any]) -> str:
        """Compose a textual snapshot of the world for prompt consumption."""

        player = state.get("player", {})
        inventory = ", ".join(player.get("inventory", [])) or "empty"
        metrics = state.get("metrics", {})
        world_constraint = state.get("world_constraint_from_prev_turn", {})
        motifs = state.get("recent_motifs", [])[-3:]
        recent_motifs = ", ".join(motifs) or "none"
        recent_major = (
            ", ".join(
                "yes" if flag else "no"
                for flag in state.get("recent_major_events", [])[-3:]
            )
            or "none"
        )

        sections = [
            (
                "Turn {turn} | Day {day} | Time {time}".format(
                    turn=state.get("turn", 0),
                    day=state.get("day", 1),
                    time=state.get("time", "dawn"),
                )
            ),
            f"Location: {state.get('current_room', 'unknown')}",
            (
                "Player: {name} — {summary}".format(
                    name=player.get("name", "Unknown"),
                    summary=player.get("summary", "").strip(),
                )
            ),
            f"Inventory: {inventory}",
            (
                "World constraint: {payload}".format(
                    payload=json.dumps(
                        world_constraint,
                        ensure_ascii=False,
                    )
                )
            ),
            f"Recent events: {self._format_recent_events(state)}",
            f"Recent motifs: {recent_motifs}",
            f"Recent major events: {recent_major}",
            (
                "Relationship summary: {text}".format(
                    text=state.get(
                        "relationship_summary",
                        RELATIONSHIP_SUMMARY_DEFAULT,
                    )
                )
            ),
            (
                "Character summary: {text}".format(
                    text=state.get("character_summary", "").strip()
                )
            ),
            (
                "Metrics: {payload}".format(
                    payload=json.dumps(metrics, ensure_ascii=False)
                )
            ),
        ]
        return "\n".join(part for part in sections if part)

    @staticmethod
    def _format_recent_events(state: Dict[str, Any]) -> str:
        events = state.get("recent_events") or []
        if not events:
            return "none"
        trimmed = [
            event for event in events[-3:] if isinstance(event, str) and event.strip()
        ]
        return "; ".join(trimmed) if trimmed else "none"

    @staticmethod
    def _derive_major_event_flag(state: Dict[str, Any]) -> str:
        flags = state.get("flags") or []
        if "mystery_figure" in flags:
            return "major_mystery_investigation"
        return "major_wall_alert"

    @staticmethod
    def _format_major_event_summary(
        effect: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        if not effect:
            return None
        status = effect.get("status_change", {})
        status_label = status.get("status", "unknown")
        duration = status.get("duration", 0)
        target = effect.get("applied_to", "unknown")
        flag = effect.get("applied_flag", "major_event")

        return f"{flag} -> {target} ({status_label}, {duration} turns)"

    @staticmethod
    def _infer_primary_npc_name(state: Dict[str, Any]) -> str:
        summary = state.get("character_summary", "")
        if summary:
            first_word = summary.split()[0].strip(",.;:")
            if first_word:
                return first_word
        return "Rhea"

    @staticmethod
    def _stringify(payload: Any) -> str:
        """Render payloads for logging without raising serialization errors."""

        try:
            text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            text = str(payload)
        if len(text) > 600:
            return text[:597] + "..."
        return text
