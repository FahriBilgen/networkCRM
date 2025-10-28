import ast
import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from fortress_director.codeaware.function_validator import FunctionCallValidator
from fortress_director.codeaware.rollback_system import RollbackSystem
from fortress_director.utils.output_validator import validate_turn_output
from fortress_director.settings import DEFAULT_WORLD_STATE
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
    FunctionNotRegisteredError,
    FunctionValidationError,
    SafeFunctionRegistry,
    Validator,
)
from fortress_director.utils.glitch_manager import GlitchManager
from fortress_director.utils.logging_config import configure_logging
from fortress_director.utils.metrics_manager import MetricManager

configure_logging()

LOGGER = logging.getLogger(__name__)

RELATIONSHIP_SUMMARY_DEFAULT = "No relationship summary available."

# Dynamic metrics mapping based on action types
ACTION_METRIC_DELTAS = {
    "interact": {"morale": 2, "knowledge": 1},  # Positive social interaction
    "dialogue": {"morale": 1, "knowledge": 2},  # Learning through conversation
    "explore": {"knowledge": 3, "morale": -1},  # Risky exploration
    "fight": {"morale": 3, "resources": -2},  # Combat boosts morale but costs resources
    "defend": {"order": 2, "morale": 1},  # Defense maintains order
    "trade": {"resources": 3, "morale": 1},  # Trading gains resources
    "rest": {"morale": 2, "order": -1},  # Rest recovers morale but reduces vigilance
    "investigate": {"knowledge": 4, "morale": -2},  # High knowledge gain but risky
    "ask": {"knowledge": 2, "morale": 1},  # Information gathering
    "ignore": {"order": -1, "morale": -1},  # Ignoring situations reduces morale/order
    "end": {},  # No changes for campaign end
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

    def test_method(self):
        """Test method to check if class parsing works."""
        return "test"

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
            return self._fresh_default()
        text = self._path.read_text(encoding="utf-8").strip()
        if not text:
            LOGGER.debug(
                "World state file %s empty; loading defaults",
                self._path,
            )
            return self._fresh_default()
        try:
            payload = json.loads(text) or {}
        except json.JSONDecodeError:
            LOGGER.warning(
                "World state file %s corrupt; loading defaults",
                self._path,
            )
            return self._fresh_default()
        if not isinstance(payload, dict):  # pragma: no cover - defensive guard
            return self._fresh_default()
        merged = self._merge_with_defaults(payload)
        return merged

    @staticmethod
    def _fresh_default() -> Dict[str, Any]:
        return deepcopy(DEFAULT_WORLD_STATE)

    @classmethod
    def _merge_with_defaults(cls, overrides: Dict[str, Any]) -> Dict[str, Any]:
        base = deepcopy(DEFAULT_WORLD_STATE)
        return cls._deep_merge(base, overrides)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = StateStore._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

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
    def update_motif(self, motif: str) -> None:
        """Update the current motif in the game state and persist."""
        state = self.state_store.snapshot()
        motifs = state.get("recent_motifs", [])
        motifs.append(motif)
        state["recent_motifs"] = motifs[-5:]
        self.state_store.persist(state)
        LOGGER.info(f"Motif updated: {motif}")

    def autonomous_actions_method(self, state):
        """Generate autonomous actions for NPCs."""
        if not self.character_agent:
            return []

        # Get NPCs from state
        npcs = []
        character_summary = state.get("character_summary", "")
        if character_summary:
            # Parse character summary like "Scout Rhea cautious; Merchant Boris opportunistic"
            entries = [e.strip() for e in character_summary.split(";") if e.strip()]
            for entry in entries:
                if " " in entry:
                    name = (
                        entry.split(" ")[0] + " " + entry.split(" ")[1]
                    )  # First two words as name
                    npcs.append(name)

        if not npcs:
            return []

        actions = []
        for npc_name in npcs:
            try:
                # Build context for autonomous action
                context = {
                    "world_context": self._build_world_context(state),
                    "current_situation": f"Turn {state.get('turn', 1)} in the siege",
                    "atmosphere": state.get("world_constraint_from_prev_turn", {}).get(
                        "atmosphere", ""
                    ),
                    "sensory_details": state.get(
                        "world_constraint_from_prev_turn", {}
                    ).get("sensory_details", ""),
                    "npc_personality": (
                        "loyal but impulsive"
                        if "Rhea" in npc_name
                        else "cautious and calculating"
                    ),
                    "relationships": {},  # Could be expanded
                    "recent_events": state.get("recent_events", []),
                }

                action = self.character_agent.autonomous_action(npc_name, context)
                if action and action.get("safe_functions"):
                    actions.append(action)
            except Exception as e:
                LOGGER.error(
                    "Failed to generate autonomous action for %s: %s", npc_name, e
                )

        return actions

    def update_character(
        self, name: str, summary: str, stats: dict = None, inventory: list = None
    ) -> None:
        """Update or add a character in the game state and persist."""
        state = self.state_store.snapshot()
        # Update character summary string
        entries = [
            e.strip()
            for e in state.get("character_summary", "").split(";")
            if e.strip()
        ]
        updated = False
        for i, entry in enumerate(entries):
            if entry.lower().startswith(name.lower()):
                entries[i] = f"{name} {summary}"
                updated = True
        if not updated:
            entries.append(f"{name} {summary}")
        state["character_summary"] = "; ".join(entries)
        # Optionally update stats and inventory for main player or named NPC
        if name == state.get("player", {}).get("name"):
            if stats:
                state["player"]["stats"] = stats
            if inventory:
                state["player"]["inventory"] = inventory
        self.state_store.persist(state)
        LOGGER.info(f"Character updated: {name}")

    def update_prompt(
        self, agent: str, new_prompt: str, persist_to_file: bool = False
    ) -> None:
        """Update the prompt for a given agent and optionally persist to file."""
        state = self.state_store.snapshot()
        prompt_files = {
            "character": "prompts/character_prompt.txt",
            "event": "prompts/event_prompt.txt",
            "judge": "prompts/judge_prompt.txt",
            "world": "prompts/world_prompt.txt",
        }
        if agent in prompt_files:
            file_path = prompt_files[agent]
            if persist_to_file:
                abs_path = Path(__file__).parent.parent / file_path
                abs_path.write_text(new_prompt, encoding="utf-8")
                LOGGER.info(f"Prompt for {agent} updated and persisted to {file_path}")
            # Update in-memory template if agent is loaded
            agent_obj = getattr(self, f"{agent}_agent", None)
            if agent_obj and hasattr(agent_obj, "prompt_template"):
                agent_obj.prompt_template.text = new_prompt
                LOGGER.info(f"Prompt for {agent} updated in memory")
        else:
            LOGGER.warning(f"Unknown agent for prompt update: {agent}")

    def mutate_safe_function(
        self,
        name: str,
        function: Optional[Callable[..., Any]] = None,
        *,
        remove: bool = False,
        validator: Optional[Validator] = None,
    ) -> None:
        """Add or remove a safe function from the registry."""

        if remove:
            try:
                self.function_registry.remove(name)
            except FunctionNotRegisteredError:
                LOGGER.info(
                    "Safe function '%s' not registered; nothing to remove", name
                )
            else:
                LOGGER.info("Safe function removed: %s", name)
            return

        if function is None:
            LOGGER.warning(
                "Safe function '%s' registration requested without a callable; skipping",
                name,
            )
            return

        self.register_safe_function(name, function, validator=validator)
        LOGGER.info("Safe function registered: %s", name)

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
    runs_dir: Path

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
        runs_dir = Path("runs") / "latest_run"
        runs_dir.mkdir(parents=True, exist_ok=True)
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
            runs_dir=runs_dir,
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

        self._metric_log_buffer = []
        glitch_info: Dict[str, Any] = {
            "roll": 0,
            "effects": [],
            "triggered_loss": False,
        }

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
            # Check for end flag at turn start
            flags = state_snapshot.get("flags", [])
            if "end" in flags:
                LOGGER.info("End flag detected, terminating early")
                return {
                    "WORLD_CONTEXT": self._build_world_context(state_snapshot),
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
                    "win_loss": {"status": "loss", "reason": "campaign_end"},
                    "narrative": "Campaign ended.",
                }
            metric_manager = MetricManager(
                state_snapshot,
                log_sink=self._metric_log_sink(),
            )
            LOGGER.debug(
                "Metrics at turn start: %s",
                metric_manager.snapshot(),
            )
            rng_seed = state_snapshot.get("rng_seed", 0)
            if not isinstance(rng_seed, int):
                try:
                    rng_seed = int(rng_seed)
                except (TypeError, ValueError):
                    rng_seed = 0
            state_snapshot["rng_seed"] = rng_seed
            glitch_manager = GlitchManager(seed=rng_seed)

            turn_limit = state_snapshot.get("turn_limit", 30)
            current_turn = state_snapshot.get(
                "current_turn", state_snapshot.get("turn", 0)
            )
            if not isinstance(current_turn, int):
                try:
                    current_turn = int(current_turn)
                except (TypeError, ValueError):
                    current_turn = 0
            if not isinstance(turn_limit, int):
                try:
                    turn_limit = int(turn_limit)
                except (TypeError, ValueError):
                    turn_limit = 30
            turn_limit = min(turn_limit, 30)

            glitch_info = glitch_manager.resolve_turn(
                metrics=metric_manager,
                turn=current_turn + 1,
                finalized=state_snapshot.get("finalized", False),
            )
            LOGGER.info(
                "Glitch resolution outcome: roll=%s, triggered_loss=%s",
                glitch_info.get("roll"),
                glitch_info.get("triggered_loss"),
            )
            LOGGER.debug(
                "Metrics after glitch resolution: %s",
                metric_manager.snapshot(),
            )

            # Periodic glitch recovery: reduce glitch by 1 every turn
            metric_manager.recover_metric("glitch", 1, cause="turn_recovery")
            LOGGER.debug(
                "Metrics after glitch recovery: %s",
                metric_manager.snapshot(),
            )
            LOGGER.info(
                "Glitch resolution outcome: roll=%s, triggered_loss=%s",
                glitch_info.get("roll"),
                glitch_info.get("triggered_loss"),
            )
            LOGGER.debug(
                "Metrics after glitch resolution: %s",
                metric_manager.snapshot(),
            )

            is_final_turn = current_turn >= turn_limit
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
                "memory_layers": state_snapshot.get("memory_layers", []),
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

            # NPC fallback: if major_event and no move_npc, activate Boris
            if event_output.get("major_event"):
                safe_funcs = event_output.get("safe_functions", [])
                has_move = any("move_npc" in str(func) for func in safe_funcs)
                if not has_move:
                    # Add fallback move_npc for Boris
                    room = state_snapshot.get("current_room", "entrance")
                    fallback = f"move_npc('Boris', '{room}')"
                    safe_funcs.append(fallback)
                    event_output["safe_functions"] = safe_funcs
                    LOGGER.info("Added NPC fallback: %s", fallback)

            # Apply metric deltas from event agent
            event_metric_deltas = event_output.get("metric_delta", {})
            if event_metric_deltas:
                LOGGER.info("Event metric deltas: %s", event_metric_deltas)
                for metric_name, delta in event_metric_deltas.items():
                    if isinstance(delta, (int, float)):
                        metric_manager.adjust_metric(
                            metric_name, delta, cause="event_agent"
                        )
                LOGGER.debug(
                    "Metrics after event deltas: %s",
                    metric_manager.snapshot(),
                )

            LOGGER.info("Resolving player choice...")
            if is_final_turn:
                event_output["options"] = []
                chosen_option = {
                    "id": "end",
                    "text": "The campaign concludes.",
                    "action_type": "end",
                }
            else:
                chosen_option = self._resolve_player_choice(
                    event_output,
                    player_choice_id,
                )
            LOGGER.info("Player choice resolved: %s", chosen_option)
            LOGGER.debug(
                "Player choice resolved: %s",
                self._stringify(chosen_option),
            )

            # Check for end flag: if action_type is 'end', terminate turn early
            if chosen_option.get("action_type") == "end":
                LOGGER.info("End flag detected, terminating turn early")
                # Build minimal result for end
                result = {
                    "WORLD_CONTEXT": world_context,
                    "scene": event_output.get("scene", ""),
                    "options": [],
                    "world": world_output,
                    "event": event_output,
                    "player_choice": chosen_option,
                    "character_reactions": [],
                    "win_loss": {"status": "loss", "reason": "campaign_end"},
                    "narrative": f"Turn {state_snapshot.get('turn', 0) + 1} | "
                    f"{chosen_option.get('text', '')} | | Campaign ended.",
                }
                return result

            # Apply dynamic metrics based on action type
            action_type = chosen_option.get("action_type", "unknown")
            metric_deltas = ACTION_METRIC_DELTAS.get(action_type.lower(), {})
            if metric_deltas:
                LOGGER.info(
                    "Applying dynamic metrics for action_type '%s': %s",
                    action_type,
                    metric_deltas,
                )
                for metric_name, delta in metric_deltas.items():
                    metric_manager.adjust_metric(
                        metric_name, delta, cause=f"action_{action_type}"
                    )
                LOGGER.debug(
                    "Metrics after dynamic changes: %s",
                    metric_manager.snapshot(),
                )
            else:
                LOGGER.debug("No dynamic metrics for action_type '%s'", action_type)

            player_record = state_snapshot.get("player") or {}
            player_inventory = player_record.get("inventory")
            if not isinstance(player_inventory, list):
                player_inventory = []
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
                    item for item in player_inventory if isinstance(item, str)
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

            # Apply room progression after major events
            if major_event_effect and event_output.get("major_event"):
                scene_text = event_output.get("scene", "").lower()
                if "mystery figure" in scene_text or "mysterious figure" in scene_text:
                    current_room = state_snapshot.get("current_room", "entrance")
                    # Use module-level helper for progression (defined below)
                    next_room = self._get_next_room(current_room)
                    if next_room:
                        LOGGER.info(
                            "Major event involves Mystery Figure, progressing from %s to %s",
                            current_room,
                            next_room,
                        )
                        try:
                            self.run_safe_function(
                                {"name": "move_room", "kwargs": {"room": next_room}},
                                metadata={"cause": "major_event_progression"},
                            )
                            LOGGER.info(
                                "Room progressed to %s after major event", next_room
                            )
                        except Exception as exc:
                            LOGGER.warning(
                                "Failed to progress room after major event: %s", exc
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
                    seed=rng_seed,
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

            # Generate autonomous NPC actions
            autonomous_actions = self.autonomous_actions_method(state_snapshot)
            if autonomous_actions:
                LOGGER.info("Applying %d autonomous actions", len(autonomous_actions))
            if autonomous_actions:
                LOGGER.info("Applying %d autonomous actions", len(autonomous_actions))
                # Apply autonomous actions through safe function system
                for action in autonomous_actions:
                    if action.get("safe_functions"):
                        for func in action["safe_functions"]:
                            try:
                                self._execute_safe_function(
                                    func, f"autonomous_{action['npc_name']}"
                                )
                            except Exception as e:
                                LOGGER.warning(
                                    "Autonomous failed for %s: %s",
                                    action["npc_name"],
                                    e,
                                )

            LOGGER.info("Updating state and persisting...")
            self._update_state(
                state,
                world_output,
                event_output,
                chosen_option,
            )
            # Tick status effects
            self.rules_engine.tick_status_effects(state)
            # Apply environmental effects
            self.rules_engine.apply_environmental_effects(state, seed=rng_seed)
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

            # Re-describe world if weather or environment changed
            weather_changed = any(
                result.get("name") == "change_weather"
                for result in safe_function_results
            )
            if weather_changed:
                LOGGER.info("Weather changed via safe function, re-describing world...")
                world_request = {
                    "WORLD_CONTEXT": self._build_world_context(final_state),
                    "room": final_state.get("current_room", "unknown"),
                }
                new_world_output = self.world_agent.describe(world_request)
                LOGGER.info("World re-described after safe function.")
                LOGGER.debug("New world output: %s", self._stringify(new_world_output))
                world_output = new_world_output  # Update for result

            final_state = self.state_store.snapshot()
            final_metrics = MetricManager(
                final_state,
                log_sink=self._metric_log_sink(),
            )
            metrics_after = final_metrics.snapshot()
            LOGGER.debug("Final metrics snapshot: %s", metrics_after)
            win_loss = self.rules_engine.evaluate_win_loss(
                final_state, final_state.get("turn", 0)
            )
            # Win/loss evaluation now handled in rules_engine
            # if glitch_info.get("triggered_loss") and win_loss["status"] == "ongoing":
            #     win_loss = {"status": "loss", "reason": "glitch_overload"}
            LOGGER.info("Win/loss status after turn: %s", win_loss)
            # Override for end game
            if chosen_option.get("id") == "end":
                win_loss = {"status": "loss", "reason": "end_game"}
                LOGGER.info("End game triggered by player choice.")
            # Set finalized flag if game ended
            if win_loss["status"] != "ongoing":
                final_state["finalized"] = True
                self.state_store.persist(final_state)
                LOGGER.info("Game finalized, state persisted.")
            narrative = self._compose_turn_narrative(
                turn=final_state.get("turn", 0),
                choice=chosen_option,
                character_output=character_output,
                glitch_effects=glitch_info.get("effects", []),
            )

            result = {
                "WORLD_CONTEXT": world_context,
                "scene": event_output.get("scene", ""),
                "options": event_output.get("options", []),
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
            result["safe_function_results"] = safe_function_results
            result["metrics_after"] = metrics_after
            result["glitch"] = {
                "roll": int(glitch_info.get("roll", 0)),
                "effects": list(glitch_info.get("effects", [])),
            }
            # Provide structured helper fields for UI consumption to avoid fragile parsing
            # Build a structured `npcs` list if not already present in the state
            try:
                npcs = final_state.get("npcs")
                if not npcs:
                    npcs = []
                    npc_fragments = final_state.get("npc_fragments", {}) or {}
                    npc_locations = final_state.get("npc_locations", {}) or {}
                    if isinstance(npc_fragments, dict) and npc_fragments:
                        for name, frag in npc_fragments.items():
                            npcs.append(
                                {
                                    "name": name,
                                    "description": frag.get("description", ""),
                                    "location": npc_locations.get(
                                        name, final_state.get("current_room", "Unknown")
                                    ),
                                }
                            )
                    else:
                        # Fallback: parse character_summary into simple name/description entries
                        character_summary = (
                            final_state.get("character_summary", "") or ""
                        )
                        for entry in [
                            e.strip() for e in character_summary.split(";") if e.strip()
                        ]:
                            parts = entry.split()
                            name = parts[0] if parts else "Unknown"
                            description = " ".join(parts[1:]) if len(parts) > 1 else ""
                            npcs.append(
                                {
                                    "name": name,
                                    "description": description,
                                    "location": final_state.get(
                                        "current_room", "Unknown"
                                    ),
                                }
                            )
                result["npcs"] = npcs
            except Exception:
                result["npcs"] = []

            # Expose safe function call history and recent room/event history for the UI
            result["safe_function_history"] = safe_function_results
            result["room_history"] = list(final_state.get("recent_events", []))[-5:]
            result["logs"] = list(self._metric_log_buffer)
            result["win_loss"] = win_loss
            result["narrative"] = narrative
            if win_loss["status"] != "ongoing":
                result["options"] = []
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
        import time

        timestamp = int(time.time() * 1000)
        turn_index = self.state_store._state.get("turn", 0)
        caller = metadata.get("source", "unknown") if metadata else "unknown"
        applied = False
        validator_verdict = "pending"
        reasons = []
        result_diff = None
        try:
            outcome = self.rollback_system.run_validated_call(
                self.function_validator,
                payload,
                metadata=metadata,
            )
            applied = True
            validator_verdict = "approved"
            result_diff = outcome  # Simplified diff
        except Exception as exc:
            validator_verdict = "rejected"
            reasons = [str(exc)]
            raise
        finally:
            # Log to audit.jsonl
            audit_entry = {
                "timestamp": timestamp,
                "turn_index": turn_index,
                "caller": caller,
                "safe_call": payload,
                "validator_verdict": validator_verdict,
                "reasons": reasons,
                "applied": applied,
            }
            self._log_audit(audit_entry)
            # Log to replay.jsonl if applied
            if applied:
                replay_entry = {
                    "timestamp": timestamp,
                    "turn_index": turn_index,
                    "caller": caller,
                    "safe_call": payload,
                    "applied_result_diff": result_diff,
                }
                self._log_replay(replay_entry)
        return outcome if applied else None

    def _register_default_safe_functions(self) -> None:
        """Register baseline safe functions used by the scenario."""
        if hasattr(self, "_safe_functions_registered"):
            return
        self._safe_functions_registered = True

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
        self.register_safe_function("adjust_logic", self._safe_adjust_logic)
        self.register_safe_function("adjust_emotion", self._safe_adjust_emotion)
        self.register_safe_function("raise_corruption", self._safe_raise_corruption)
        self.register_safe_function("advance_turn", self._safe_advance_turn)
        self.register_safe_function(
            "modify_resources",
            self._safe_modify_resources,
            validator=self._validate_modify_resources_call,
        )
        self.register_safe_function(
            "adjust_metric",
            self._safe_adjust_metric,
            validator=self._validate_adjust_metric_call,
        )
        self.register_safe_function(
            "move_room",
            self._safe_move_room,
            validator=self._validate_move_room_call,
        )

    def _log_audit(self, entry: Dict[str, Any]) -> None:
        """Append audit entry to audit.jsonl."""
        audit_file = self.runs_dir / "audit.jsonl"
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def _log_replay(self, entry: Dict[str, Any]) -> None:
        """Append replay entry to replay.jsonl."""
        replay_file = self.runs_dir / "replay.jsonl"
        with open(replay_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

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

    def _validate_modify_resources_call(
        self,
        call: FunctionCall,
    ) -> FunctionCall:
        if call.args:
            raise FunctionValidationError(
                "modify_resources does not accept positional arguments",
            )
        kwargs = dict(call.kwargs)
        amount_raw = kwargs.get("amount", kwargs.get("delta", 0))
        try:
            amount = int(amount_raw)
        except (TypeError, ValueError) as exc:
            raise FunctionValidationError(
                "modify_resources requires integer amount"
            ) from exc
        cause_raw = kwargs.get("cause", "safe_modify_resources")
        cause = str(cause_raw).strip() or "safe_modify_resources"
        sanitized = {"amount": amount, "cause": cause}
        return FunctionCall(
            name=call.name,
            args=(),
            kwargs=sanitized,
            metadata=call.metadata,
        )

    def _validate_adjust_metric_call(
        self,
        call: FunctionCall,
    ) -> FunctionCall:
        if call.args:
            raise FunctionValidationError(
                "adjust_metric does not accept positional arguments",
            )
        kwargs = dict(call.kwargs)
        metric_raw = kwargs.get("metric")
        if not isinstance(metric_raw, str) or not metric_raw.strip():
            raise FunctionValidationError("adjust_metric requires a metric name")
        metric = metric_raw.strip()
        try:
            delta = int(kwargs.get("delta", 0))
        except (TypeError, ValueError) as exc:
            raise FunctionValidationError(
                "adjust_metric requires integer delta"
            ) from exc
        cause_raw = kwargs.get("cause", f"adjust_metric:{metric}")
        cause = str(cause_raw).strip() or f"adjust_metric:{metric}"
        sanitized = {"metric": metric, "delta": delta, "cause": cause}
        return FunctionCall(
            name=call.name,
            args=(),
            kwargs=sanitized,
            metadata=call.metadata,
        )

    def _validate_move_room_call(
        self,
        call: FunctionCall,
    ) -> FunctionCall:
        if call.args:
            raise FunctionValidationError(
                "move_room does not accept positional arguments",
            )
        kwargs = dict(call.kwargs)
        room = kwargs.get("room")
        if not isinstance(room, str) or not room.strip():
            raise FunctionValidationError(
                "move_room requires a non-empty 'room' string",
            )
        sanitized = {"room": room.strip()}
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

    def _safe_modify_resources(
        self,
        *,
        amount: int,
        cause: str,
    ) -> Dict[str, Any]:
        state = self.state_store.snapshot()
        manager = MetricManager(state, log_sink=self._metric_log_sink())
        value = manager.modify_resources(amount, cause=cause)
        self.state_store.persist(state)
        return {"resources": value}

    def _safe_move_room(
        self,
        *,
        room: str,
    ) -> Dict[str, str]:
        state = self.state_store.snapshot()
        state["current_room"] = room
        self.state_store.persist(state)
        return {
            "room": room,
        }

    def _safe_adjust_metric(
        self,
        *,
        metric: str,
        delta: int,
        cause: str,
    ) -> Dict[str, Any]:
        state = self.state_store.snapshot()
        manager = MetricManager(state, log_sink=self._metric_log_sink())
        value = manager.adjust_metric(metric, delta, cause=cause)
        self.state_store.persist(state)
        return {metric: value}

    def _safe_adjust_logic(self) -> Dict[str, Any]:
        return self._adjust_score("logic_score", 1)

    def _safe_adjust_emotion(self) -> Dict[str, Any]:
        return self._adjust_score("emotion_score", 1)

    def _safe_raise_corruption(self) -> Dict[str, Any]:
        return self._adjust_score("corruption", 1)

    def _safe_advance_turn(self) -> Dict[str, Any]:
        state = self.state_store.snapshot()
        previous_turn = state.get("current_turn")
        if not isinstance(previous_turn, int):
            previous_turn = int(state.get("turn", 0))
        next_turn = previous_turn + 1
        state["current_turn"] = next_turn
        state["turn"] = max(int(state.get("turn", next_turn)), next_turn)
        self.state_store.persist(state)
        return {"current_turn": state["current_turn"], "turn": state["turn"]}

    def _adjust_score(self, key: str, delta: int) -> Dict[str, Any]:
        state = self.state_store.snapshot()
        scores = state.setdefault("scores", {})
        current_value = scores.get(key, 0)
        try:
            current_value = int(current_value)
        except (TypeError, ValueError):
            current_value = 0
        scores[key] = current_value + delta
        self.state_store.persist(state)
        return {"scores": dict(scores)}

    def _metric_log_sink(self) -> List[Dict[str, Any]]:
        buffer = getattr(self, "_metric_log_buffer", None)
        if buffer is None:
            buffer = []
            self._metric_log_buffer = buffer
        return buffer

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
                try:
                    node = ast.parse(entry, mode="eval").body
                    if not isinstance(node, ast.Call) or not isinstance(
                        node.func, ast.Name
                    ):
                        raise ValueError("Unsupported safe function expression")
                    func_name = node.func.id
                    args = [ast.literal_eval(arg) for arg in node.args]
                    kwargs = {
                        kw.arg: ast.literal_eval(kw.value)
                        for kw in node.keywords
                        if kw.arg is not None
                    }
                    payload: Dict[str, Any] = {"name": func_name}
                    normalized_kwargs = self._normalize_safe_function_kwargs(
                        func_name,
                        args,
                        kwargs,
                    )
                    if normalized_kwargs:
                        payload["kwargs"] = normalized_kwargs
                    remaining_args = [value for value in args if value is not None]
                    if remaining_args and func_name not in {
                        "change_weather",
                        "spawn_item",
                        "move_npc",
                    }:
                        payload["args"] = remaining_args
                    metadata: Dict[str, Any] = {"source": source}
                    normalized.append((payload, metadata))
                except Exception as exc:
                    LOGGER.warning(
                        "Failed to parse safe function call '%s': %s",
                        entry,
                        exc,
                    )
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

    @staticmethod
    def _normalize_safe_function_kwargs(
        name: str,
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        def _as_text(value: Any) -> str:
            text = str(value) if value is not None else ""
            return text.strip()

        if name == "change_weather":
            atmosphere = kwargs.get("atmosphere")
            details = kwargs.get("sensory_details")
            if args:
                atmosphere = args[0]
                if len(args) > 1:
                    details = args[1]
            atmosphere_text = _as_text(atmosphere)
            if not atmosphere_text:
                raise ValueError("change_weather requires an atmosphere")
            details_text = _as_text(details) or "The weather shifts subtly."
            return {
                "atmosphere": atmosphere_text,
                "sensory_details": details_text,
            }

        if name == "spawn_item":
            item_id = kwargs.get("item_id")
            target = kwargs.get("target")
            if args:
                if len(args) > 0:
                    item_id = args[0]
                if len(args) > 1:
                    target = args[1]
            item_text = _as_text(item_id)
            target_text = _as_text(target)
            if not item_text or not target_text:
                raise ValueError("spawn_item requires item_id and target")
            return {
                "item_id": item_text,
                "target": target_text,
            }

        if name == "move_npc":
            npc_id = kwargs.get("npc_id") or kwargs.get("npc_name")
            location = kwargs.get("location") or kwargs.get("target")
            if args:
                if len(args) > 0:
                    npc_id = args[0]
                if len(args) > 1:
                    location = args[1]
            npc_text = _as_text(npc_id)
            location_text = _as_text(location)
            if not npc_text or not location_text:
                raise ValueError("move_npc requires npc identifier and location")
            return {
                "npc_id": npc_text,
                "location": location_text,
            }

        cleaned = {
            key: value for key, value in kwargs.items() if key and value is not None
        }
        return cleaned

    def _resolve_player_choice(
        self,
        event_output: Dict[str, Any],
        player_choice_id: Optional[str],
    ) -> Dict[str, Any]:
        raw_options = event_output.get("options")
        options: List[Dict[str, Any]] = []
        if isinstance(raw_options, list):
            options = [opt for opt in raw_options if isinstance(opt, dict)]
        if not options:
            fallback_option = {
                "id": "opt_1",
                "text": "Hold position and watch the storm.",
                "action_type": "observe",
            }
            event_output["options"] = [fallback_option]
            options = [fallback_option]

        selected: Optional[Dict[str, Any]] = None
        if player_choice_id:
            for option in options:
                if str(option.get("id")) == str(player_choice_id):
                    selected = option
                    break
        if selected is None:
            selected = options[0]

        resolved = {}
        for key in ("id", "text", "action_type"):
            value = selected.get(key, "")
            if not isinstance(value, str):
                value = str(value)
            resolved[key] = value.strip() or f"{key}_unknown"

        return resolved

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

    def _build_fallback_reaction(
        self,
        state: Dict[str, Any],
        chosen_option: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        npc_name = self._infer_primary_npc_name(state)
        speech_hint = ""
        if isinstance(chosen_option, dict):
            candidate = chosen_option.get("text", "")
            if isinstance(candidate, str):
                speech_hint = candidate.strip()
        fallback_speech = (speech_hint or "Holding the line until the storm breaks.")[
            :200
        ]
        return {
            "name": npc_name,
            "intent": "defend",
            "action": "hold_position",
            "speech": fallback_speech,
            "effects": {},
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

    def _compose_turn_narrative(
        self,
        *,
        turn: int,
        choice: Dict[str, Any],
        character_output: List[Dict[str, Any]],
        glitch_effects: List[str],
    ) -> str:
        """Generate a compact textual summary for the turn result."""

        if not isinstance(choice, dict):
            choice = {}
        choice_text = str(choice.get("text", "")).strip()
        reaction_text = ""
        if character_output:
            primary = character_output[0]
            if isinstance(primary, dict):
                reaction_text = str(
                    primary.get("speech") or primary.get("action") or ""
                ).strip()
        glitch_text = ""
        if glitch_effects:
            glitch_text = str(glitch_effects[0]).strip()
        parts = [
            f"Turn {turn}",
            choice_text,
            reaction_text,
            glitch_text,
        ]
        narrative = " | ".join(part for part in parts if part)
        return narrative[:240]

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

    def _update_state(
        self,
        state: Dict[str, Any],
        world_output: Dict[str, Any],
        event_output: Dict[str, Any],
        chosen_option: Dict[str, Any],
    ) -> None:
        """Update state after turn: increment turn, trim lists, add memory."""
        # Increment turn
        current_turn = state.get("current_turn", 0)
        state["current_turn"] = current_turn + 1
        state["turn"] = state["current_turn"]

        # Update world constraint from previous turn
        state["world_constraint_from_prev_turn"] = {
            "atmosphere": world_output.get("atmosphere", ""),
            "sensory_details": world_output.get("sensory_details", ""),
        }

        # Trim recent_motifs to maxlen=3
        recent_motifs = state.get("recent_motifs", [])
        if len(recent_motifs) > 3:
            recent_motifs = recent_motifs[-3:]
        state["recent_motifs"] = recent_motifs

        # Add new motif if major_event
        if event_output.get("major_event"):
            new_motif = chosen_option.get("action_type", "unknown")
            if new_motif not in recent_motifs:
                recent_motifs.append(new_motif)
                if len(recent_motifs) > 3:
                    recent_motifs.pop(0)
            state["recent_motifs"] = recent_motifs

        # Trim recent_events to maxlen=3
        recent_events = state.get("recent_events", [])
        if len(recent_events) > 3:
            recent_events = recent_events[-3:]
        state["recent_events"] = recent_events

        # Add new event summary
        scene = event_output.get("scene", "")
        new_event = scene[:200] + "..." if len(scene) > 200 else scene
        recent_events.append(new_event)
        if len(recent_events) > 3:
            recent_events.pop(0)
        state["recent_events"] = recent_events

        # Add to memory_layers
        memory_layers = state.get("memory_layers", [])
        choice_text = chosen_option.get("text", "")
        scene_part = event_output.get("scene", "")[:100]
        turn_summary = f"Turn {current_turn + 1}: {choice_text} -> "
        turn_summary += f"{scene_part}..."
        memory_layers.append(turn_summary)
        # Memory summarizer every 3 turns to break token echo loops
        if (current_turn + 1) % 3 == 0 and len(memory_layers) >= 3:
            summary = " | ".join(memory_layers[-3:])[:200] + "..."
            memory_layers.append(f"Memory summary: {summary}")
        if len(memory_layers) > 5:  # Keep last 5
            memory_layers = memory_layers[-5:]
        state["memory_layers"] = memory_layers

        # Reset major_flag_set if it was set
        if state.get("major_flag_set"):
            state["major_flag_set"] = False

        # Update major_events_triggered
        if event_output.get("major_event"):
            major_triggered = state.get("major_events_triggered", 0) + 1
            state["major_events_triggered"] = major_triggered
            state["major_event_last_turn"] = current_turn + 1
            # Limit major events to prevent over-triggering
            if major_triggered >= 5:
                LOGGER.warning("Major event limit %d reached", major_triggered)
                event_output["major_event"] = False


def simulate(n_turns: int = 3, seed: int = 123) -> None:
    """Run a deterministic mini-simulation using the packaged orchestrator."""

    orchestrator = Orchestrator.build_default()
    baseline = deepcopy(DEFAULT_WORLD_STATE)
    baseline["rng_seed"] = seed
    baseline["turn"] = 0
    baseline["current_turn"] = 0
    MetricManager(baseline, log_sink=[])
    orchestrator.state_store.persist(baseline)

    for turn_index in range(n_turns):
        result = orchestrator.run_turn()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        status = result.get("win_loss", {}).get("status", "ongoing")
        if status != "ongoing":
            break
        if turn_index == 0:
            orchestrator.run_safe_function(
                {
                    "name": "adjust_metric",
                    "kwargs": {
                        "metric": "order",
                        "delta": 15,
                        "cause": "demo_order_boost",
                    },
                }
            )
            orchestrator.run_safe_function(
                {
                    "name": "adjust_metric",
                    "kwargs": {
                        "metric": "morale",
                        "delta": 18,
                        "cause": "demo_morale_boost",
                    },
                }
            )
        if turn_index == 1:
            orchestrator.run_safe_function(
                {
                    "name": "adjust_metric",
                    "kwargs": {
                        "metric": "glitch",
                        "delta": -10,
                        "cause": "demo_glitch_stabilisation",
                    },
                }
            )
    # end simulate()

    def _get_next_room(self, current_room: str) -> str | None:
        """Get the next room in the progression sequence.

        Args:
            current_room: Current room name

        Returns:
            Next room name or None if at the end of progression
        """
        room_progression = {
            "entrance": "courtyard",
            "courtyard": "inner_wall",
            "inner_wall": None,  # End of progression
        }
        return room_progression.get(current_room)
