"""Turn manager orchestrating the 3-agent pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fortress_director.core import player_action_catalog
from fortress_director.core.function_registry import (
    FUNCTION_REGISTRY,
    apply_theme_overrides,
)
from fortress_director.core.functions.function_schema import SafeFunctionMeta
from fortress_director.core.state_store import DEFAULT_TURN_LIMIT, GameState
from fortress_director.core.threat_model import ThreatModel, ThreatSnapshot
from fortress_director.core.state_archive import StateArchive
from fortress_director.ending.evaluator import evaluate_ending
from fortress_director.narrative.event_graph import EventGraph, EventNode
from fortress_director.narrative.final_engine import FinalEngine
from fortress_director.narrative.theme_graph_loader import load_event_graph_for_theme
from fortress_director.pipeline.event_curve import EventCurve
from fortress_director.pipeline.endgame_detector import EndgameDetector
from fortress_director.pipeline.world_tick import world_tick
from fortress_director.settings import SETTINGS
from fortress_director.themes.loader import BUILTIN_THEMES, load_theme_from_file
from fortress_director.themes.schema import ThemeConfig

from ..agents import DirectorAgent, PlannerAgent, WorldRendererAgent
from . import function_executor, turn_trace
from fortress_director.llm.metrics_logger import register_metrics_callback
from fortress_director.llm.profiler import LLMCallMetrics

LOGGER = logging.getLogger(__name__)
TURN_PERF_LOG = SETTINGS.log_dir / "turn_perf.log"

try:
    _DEFAULT_THEME_CONFIG: ThemeConfig | None = load_theme_from_file(
        BUILTIN_THEMES["siege_default"]
    )
except Exception as theme_exc:  # pragma: no cover - defensive
    LOGGER.warning("Unable to load default theme config: %s", theme_exc)
    _DEFAULT_THEME_CONFIG = None


@dataclass
class TurnResult:
    narrative: str
    ui_events: List[Dict[str, Any]]
    state_delta: Dict[str, Any]
    player_options: List[Dict[str, Any]]
    executed_actions: List[Dict[str, Any]]
    atmosphere: Optional[Dict[str, Any]]
    trace_file: Optional[str]
    turn_number: int
    is_final: bool = False
    ending_id: Optional[str] = None
    threat_snapshot: ThreatSnapshot | None = None
    event_seed: Optional[str] = None
    final_directive: Optional[Dict[str, Any]] = None
    event_node_id: Optional[str] = None
    event_node_description: Optional[str] = None
    event_node_is_final: bool = False
    next_event_node_id: Optional[str] = None
    world_tick_delta: Dict[str, Any] | None = None
    final_payload: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        threat_payload = (
            asdict(self.threat_snapshot) if self.threat_snapshot is not None else None
        )
        return {
            "narrative": self.narrative,
            "ui_events": self.ui_events,
            "state_delta": self.state_delta,
            "player_options": self.player_options,
            "executed_actions": self.executed_actions,
            "atmosphere": self.atmosphere,
            "trace_file": self.trace_file,
            "turn_number": self.turn_number,
            "is_final": self.is_final,
            "ending_id": self.ending_id,
            "threat": threat_payload,
            "event_seed": self.event_seed,
            "final_directive": self.final_directive,
            "event_node_id": self.event_node_id,
            "event_node_description": self.event_node_description,
            "event_node_is_final": self.event_node_is_final,
            "next_event_node_id": self.next_event_node_id,
            "world_tick_delta": self.world_tick_delta,
            "final_payload": self.final_payload,
        }


class TurnManager:
    """Wires the three agents with state utilities."""

    def __init__(
        self,
        *,
        director_agent: Optional[DirectorAgent] = None,
        planner_agent: Optional[PlannerAgent] = None,
        world_renderer_agent: Optional[WorldRendererAgent] = None,
        threat_model: ThreatModel | None = None,
        event_curve: EventCurve | None = None,
        endgame_detector: EndgameDetector | None = None,
        event_graph: EventGraph | None = None,
        function_executor_module=function_executor,
        final_engine: FinalEngine | None = None,
    ) -> None:
        self.director_agent = director_agent or DirectorAgent()
        self.planner_agent = planner_agent or PlannerAgent()
        self.world_renderer_agent = world_renderer_agent or WorldRendererAgent()
        self.threat_model = threat_model or ThreatModel({})
        self.event_curve = event_curve or EventCurve({})
        self.endgame_detector = endgame_detector or EndgameDetector()
        self._function_executor = function_executor_module
        self.final_engine = final_engine or FinalEngine(
            world_renderer_agent=self.world_renderer_agent
        )
        self._event_graph_cache: Dict[str, EventGraph] = {}
        if event_graph is not None:
            self._event_graph_cache["_override"] = event_graph
        self._theme_registry_cache: Dict[str, Dict[str, SafeFunctionMeta]] = {}
        self._active_theme_id: str | None = None

    def run_turn(
        self,
        game_state: GameState,
        player_choice: Optional[Union[Dict[str, Any], str]] = None,
        player_action_context: Optional[Dict[str, Any]] = None,
        theme: ThemeConfig | None = None,
        archive: StateArchive | None = None,
    ) -> TurnResult:
        """Execute a full turn and return the UI payload."""

        LOGGER.info("Starting turn run (choice=%s)", player_choice)
        active_theme = theme or _DEFAULT_THEME_CONFIG
        if active_theme is None:
            raise ValueError("Theme configuration is required.")
        self._ensure_theme_state(game_state, active_theme)
        if not self.threat_model.has_baseline():
            base_value = active_theme.initial_metrics.get("threat")
            if base_value is not None:
                self.threat_model.set_base_threat(int(base_value))
        event_graph = self._get_event_graph(active_theme)
        self._ensure_planner_theme(active_theme)
        if self._should_trigger_final_mode(game_state):
            LOGGER.info("Turn limit reached; triggering final engine.")
            return self._run_final_mode(game_state)
        if game_state.game_over:
            LOGGER.info("Game already marked as over; returning terminal state.")
            return self._build_terminal_result(game_state)
        llm_metrics: List[LLMCallMetrics] = []
        unsubscribe = register_metrics_callback(llm_metrics.append)
        turn_started = time.perf_counter()
        turn_number = 0
        threat_snapshot: ThreatSnapshot | None = None
        try:
            world_tick_delta = world_tick(game_state)
            world_tick_summary = world_tick_delta.pop("world_tick_summary", {})
            if world_tick_delta:
                game_state.apply_delta(world_tick_delta)
            turn_number = self._advance_turn_counter(game_state)
            projected_state = game_state.get_projected_state()
            threat_snapshot = self.threat_model.compute(game_state)
            current_event_node = self._active_event_node(game_state, event_graph)
            event_seed = self.event_curve.next_event(threat_snapshot, game_state)
            endgame_status = self.endgame_detector.check(
                game_state, threat_snapshot, event_node=current_event_node
            )
            choice_id = _extract_choice_id(player_choice)
            director_output = self.run_director_sync(
                projected_state,
                choice_id,
                threat_snapshot=threat_snapshot,
                event_seed=event_seed,
                endgame_directive=endgame_status,
                event_node=current_event_node,
                archive=archive,
                turn_number=game_state.turn,
            )
            scene_intent = director_output["scene_intent"]
            LOGGER.debug("Director intent: %s", scene_intent)
            max_calls = 2 if endgame_status.get("final_trigger") else None
            planner_output = self.run_planner_sync(
                projected_state,
                scene_intent,
                player_action_context=player_action_context,
                max_calls=max_calls,
            )
            planned_actions = planner_output.get("planned_actions", [])
            LOGGER.debug("Planner produced %d actions", len(planned_actions))
            executor_payload = self._function_executor.apply_actions(
                game_state,
                planned_actions,
            )
            world_state = executor_payload["world_state"]
            executed_actions = executor_payload["executed_actions"]
            state_delta = executor_payload["state_delta"]
            LOGGER.debug("Executor mutated state: %s", state_delta)
            render_payload = self.run_renderer_sync(
                world_state,
                executed_actions,
                threat_phase=threat_snapshot.phase if threat_snapshot else None,
                event_seed=event_seed,
                event_node=current_event_node,
                world_tick_delta=world_tick_summary,
            )
            LOGGER.info(
                "Turn completed with narrative: %s", render_payload["narrative_block"]
            )
            next_event_node = event_graph.next_node(
                current_event_node, game_state, threat_snapshot
            )
            game_state.last_event_node = next_event_node.id
            normalized_choice = _normalize_choice_payload(player_choice)
            trace_file = _persist_trace(
                world_state,
                normalized_choice,
                projected_state,
                director_output,
                planner_output,
                executed_actions,
                state_delta,
                render_payload,
                threat_snapshot,
                event_seed,
                endgame_status,
                world_tick_summary,
                {
                    "current_node": current_event_node.id,
                    "next_node": next_event_node.id,
                },
            )
            # Sanitize player options...
            catalog_actions = player_action_catalog.load_actions()
            player_options = []
            for entry in catalog_actions[:4]:
                player_options.append(
                    {
                        "id": entry.get("id"),
                        "label": entry.get("label"),
                        "requires": entry.get("requires", []),
                    }
                )

            result = TurnResult(
                narrative=render_payload["narrative_block"],
                ui_events=render_payload.get("npc_dialogues", []),
                state_delta=state_delta,
                player_options=player_options,
                executed_actions=executed_actions,
                atmosphere=render_payload.get("atmosphere", {}),
                trace_file=trace_file,
                turn_number=turn_number,
                is_final=bool(game_state.game_over),
                ending_id=game_state.ending_id,
                threat_snapshot=threat_snapshot,
                event_seed=event_seed,
                final_directive=endgame_status,
                event_node_id=current_event_node.id,
                event_node_description=current_event_node.description,
                event_node_is_final=current_event_node.is_final,
                next_event_node_id=next_event_node.id,
                world_tick_delta=world_tick_summary,
            )
            if current_event_node.is_final:
                result.is_final = True
            self._maybe_finalize_theme(game_state, result, active_theme)
            return result
        finally:
            unsubscribe()
            duration_ms = (time.perf_counter() - turn_started) * 1000.0
            phase = (
                getattr(threat_snapshot, "phase", "unknown")
                if threat_snapshot
                else "unknown"
            )
            self._log_turn_perf(
                turn_number=turn_number,
                duration_ms=duration_ms,
                llm_metrics=llm_metrics,
                phase=phase,
            )

    def run_director_sync(
        self,
        projected_state: Dict[str, Any],
        player_choice: Optional[str],
        *,
        threat_snapshot: ThreatSnapshot | None,
        event_seed: str | None,
        endgame_directive: Dict[str, Any] | None,
        event_node: "EventNode" | None,
        archive: StateArchive | None = None,
        turn_number: int = 0,
    ) -> Dict[str, Any]:
        return self.director_agent.generate_intent(
            projected_state,
            player_choice,
            threat_snapshot=threat_snapshot,
            event_seed=event_seed,
            endgame_directive=endgame_directive,
            event_node=event_node,
            archive=archive,
            turn_number=turn_number,
        )

    async def run_director_async(
        self,
        projected_state: Dict[str, Any],
        player_choice: Optional[str],
        *,
        threat_snapshot: ThreatSnapshot | None,
        event_seed: str | None,
        endgame_directive: Dict[str, Any] | None,
        event_node: "EventNode" | None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.run_director_sync,
            projected_state,
            player_choice,
            threat_snapshot=threat_snapshot,
            event_seed=event_seed,
            endgame_directive=endgame_directive,
            event_node=event_node,
        )

    def run_planner_sync(
        self,
        projected_state: Dict[str, Any],
        scene_intent: Dict[str, Any],
        *,
        player_action_context: Dict[str, Any] | None = None,
        max_calls: int | None = None,
    ) -> Dict[str, Any]:
        return self.planner_agent.plan_actions(
            projected_state,
            scene_intent,
            player_action_context=player_action_context,
            max_calls=max_calls,
        )

    async def run_planner_async(
        self,
        projected_state: Dict[str, Any],
        scene_intent: Dict[str, Any],
        *,
        player_action_context: Dict[str, Any] | None = None,
        max_calls: int | None = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.run_planner_sync,
            projected_state,
            scene_intent,
            player_action_context=player_action_context,
            max_calls=max_calls,
        )

    def run_renderer_sync(
        self,
        world_state: Dict[str, Any],
        executed_actions: List[Dict[str, Any]],
        *,
        threat_phase: str | None = None,
        event_seed: str | None = None,
        event_node: "EventNode" | None = None,
        world_tick_delta: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return self.world_renderer_agent.render(
            world_state,
            executed_actions,
            threat_phase=threat_phase,
            event_seed=event_seed,
            event_node=event_node,
            world_tick_delta=world_tick_delta,
        )

    async def run_renderer_async(
        self,
        world_state: Dict[str, Any],
        executed_actions: List[Dict[str, Any]],
        *,
        threat_phase: str | None = None,
        event_seed: str | None = None,
        event_node: "EventNode" | None = None,
        world_tick_delta: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self.run_renderer_sync,
            world_state,
            executed_actions,
            threat_phase=threat_phase,
            event_seed=event_seed,
            event_node=event_node,
            world_tick_delta=world_tick_delta,
        )

    def _ensure_theme_state(self, game_state: GameState, theme: ThemeConfig) -> None:
        snapshot = game_state.snapshot()
        if snapshot.get("theme_id") == theme.id:
            return
        theme_state = GameState.from_theme_config(theme)
        themed_snapshot = theme_state.snapshot()
        themed_snapshot["_theme_turn_started"] = False
        game_state.replace(themed_snapshot)

    def _ensure_planner_theme(self, theme: ThemeConfig) -> None:
        theme_id = theme.id or "default"
        if self._active_theme_id == theme_id:
            return
        metadata = self._get_theme_function_registry(theme)
        self.planner_agent.set_theme_metadata(metadata)
        self._active_theme_id = theme_id

    def _get_theme_function_registry(
        self, theme: ThemeConfig
    ) -> Dict[str, SafeFunctionMeta]:
        theme_id = theme.id or "default"
        if theme_id not in self._theme_registry_cache:
            self._theme_registry_cache[theme_id] = apply_theme_overrides(
                FUNCTION_REGISTRY, theme
            )
        return self._theme_registry_cache[theme_id]

    def _get_event_graph(self, theme: ThemeConfig) -> EventGraph:
        theme_id = theme.id or "default"
        if theme_id not in self._event_graph_cache:
            self._event_graph_cache[theme_id] = load_event_graph_for_theme(theme)
        return self._event_graph_cache[theme_id]

    def _advance_turn_counter(self, game_state: GameState) -> int:
        snapshot = game_state.snapshot()
        metrics = snapshot.setdefault("metrics", {})
        raw_turn = metrics.get("turn", snapshot.get("turn", 0))
        try:
            current_turn = int(raw_turn)
        except (TypeError, ValueError):
            current_turn = 0
        started = bool(snapshot.get("_theme_turn_started"))
        if started:
            current_turn = max(1, current_turn + 1)
        else:
            current_turn = max(1, current_turn)
            snapshot["_theme_turn_started"] = True
        metrics["turn"] = current_turn
        snapshot["turn"] = current_turn
        game_state.replace(snapshot)
        return current_turn

    def _should_trigger_final_mode(self, game_state: GameState) -> bool:
        snapshot = game_state.snapshot()
        if snapshot.get("_final_mode_complete"):
            return False
        try:
            return game_state.turn >= game_state.turn_limit
        except AttributeError:
            return False

    def _run_final_mode(self, game_state: GameState) -> TurnResult:
        threat_snapshot = self.threat_model.compute(game_state)
        final_payload = self.final_engine.run(
            game_state,
            threat_snapshot=threat_snapshot,
        )
        path_info = final_payload.get("final_path") or {}
        ending_id = path_info.get("id")
        if ending_id:
            game_state.ending_id = ending_id
        game_state.game_over = True
        narrative_block = final_payload.get("final_narrative") or {}
        narrative_text = (
            narrative_block.get("subtitle")
            or narrative_block.get("decision_summary")
            or narrative_block.get("title")
            or path_info.get("title")
            or "Finale achieved."
        )
        projected_state = game_state.get_projected_state()
        trace_file = _persist_trace(
            game_state.snapshot(),
            None,
            projected_state,
            {"scene_intent": {"final_mode": True}},
            {"planned_actions": final_payload.get("final_actions", [])},
            final_payload.get("final_actions", []),
            {},
            narrative_block,
            threat_snapshot,
            None,
            None,
            {},
            {"current_node": None},
            final_result=final_payload,
        )
        game_state.apply_delta({"_final_mode_complete": True})
        return TurnResult(
            narrative=narrative_text,
            ui_events=narrative_block.get("npc_fates")
            or final_payload.get("npc_outcomes", []),
            state_delta={},
            player_options=[],
            executed_actions=final_payload.get("final_actions", []),
            atmosphere=narrative_block.get("atmosphere"),
            trace_file=trace_file,
            turn_number=game_state.turn,
            is_final=True,
            ending_id=game_state.ending_id,
            threat_snapshot=threat_snapshot,
            final_payload=final_payload,
        )

    def _active_event_node(
        self, game_state: GameState, event_graph: EventGraph
    ) -> EventNode:
        node_id = game_state.last_event_node or event_graph.entry_id
        if not game_state.last_event_node:
            game_state.last_event_node = node_id
        try:
            return event_graph.get_node(node_id)
        except KeyError:
            fallback_id = event_graph.entry_id
            game_state.last_event_node = fallback_id
            return event_graph.get_node(fallback_id)

    def _build_terminal_result(self, game_state: GameState) -> TurnResult:
        snapshot = game_state.snapshot()
        metrics = snapshot.get("metrics") or {}
        raw_turn = metrics.get("turn") or snapshot.get("turn") or 0
        try:
            turn_number = int(raw_turn)
        except (TypeError, ValueError):
            turn_number = 0
        theme_meta = snapshot.get("theme") or {}
        theme_label = (
            theme_meta.get("label")
            or theme_meta.get("id")
            or snapshot.get("theme_id")
            or "Scenario"
        )
        narrative = f"{theme_label} complete."
        if game_state.ending_id:
            narrative = f"{theme_label} complete ({game_state.ending_id} ending)."
        return TurnResult(
            narrative=narrative,
            ui_events=[],
            state_delta={},
            player_options=[],
            executed_actions=[],
            atmosphere={},
            trace_file=None,
            turn_number=turn_number,
            is_final=True,
            ending_id=game_state.ending_id,
        )

    def _maybe_finalize_theme(
        self,
        game_state: GameState,
        result: TurnResult,
        theme: ThemeConfig,
    ) -> None:
        metrics = game_state.snapshot().get("metrics") or {}
        try:
            turn_value = int(metrics.get("turn", 0))
        except (TypeError, ValueError):
            turn_value = 0
        try:
            turn_limit = int(getattr(game_state, "turn_limit", DEFAULT_TURN_LIMIT))
        except (TypeError, ValueError):
            turn_limit = DEFAULT_TURN_LIMIT
        if turn_value < turn_limit:
            return
        ending_id = evaluate_ending(game_state, theme)
        game_state.game_over = True
        game_state.ending_id = ending_id
        result.is_final = True
        result.ending_id = ending_id

    def _log_turn_perf(
        self,
        *,
        turn_number: int,
        duration_ms: float,
        llm_metrics: List[LLMCallMetrics],
        phase: str | None,
    ) -> None:
        payload = {
            "turn": int(turn_number),
            "duration_ms": round(duration_ms, 3),
            "llm_calls": len(llm_metrics),
            "llm_failures": sum(1 for metric in llm_metrics if not metric.success),
            "phase": phase or "unknown",
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        try:
            TURN_PERF_LOG.parent.mkdir(parents=True, exist_ok=True)
            with TURN_PERF_LOG.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except OSError as exc:  # pragma: no cover - telemetry best-effort
            LOGGER.debug("Unable to write turn perf log: %s", exc)


_DEFAULT_MANAGER = TurnManager()


def run_turn(
    game_state: GameState,
    player_choice: Optional[Union[Dict[str, Any], str]] = None,
    player_action_context: Optional[Dict[str, Any]] = None,
    theme: ThemeConfig | None = None,
    archive: StateArchive | None = None,
) -> TurnResult:
    """Convenience wrapper that uses the default manager."""

    return _DEFAULT_MANAGER.run_turn(
        game_state,
        player_choice=player_choice,
        player_action_context=player_action_context,
        theme=theme,
        archive=archive,
    )


def _persist_trace(
    world_state: Dict[str, Any],
    player_choice: Optional[Dict[str, Any]],
    projected_state: Dict[str, Any],
    director_output: Dict[str, Any],
    planner_output: Dict[str, Any],
    executed_actions: Any,
    state_delta: Dict[str, Any],
    render_payload: Dict[str, Any],
    threat_snapshot: ThreatSnapshot | None,
    event_seed: str | None,
    final_directive: Dict[str, Any] | None,
    world_tick_delta: Dict[str, Any] | None,
    event_graph: Dict[str, str] | None = None,
    final_result: Dict[str, Any] | None = None,
) -> Optional[str]:
    """Persist the trace and return file path if successful."""

    try:
        turn_index = int(world_state.get("turn", 0))
    except (TypeError, ValueError):
        turn_index = 0
    payload = {
        "turn": turn_index,
        "player_choice": player_choice,
        "projected_state": projected_state,
        "director_output": director_output,
        "planner_output": planner_output,
        "executed_actions": executed_actions,
        "state_delta": state_delta,
        "render_payload": render_payload,
        "threat": asdict(threat_snapshot) if threat_snapshot else None,
        "event_seed": event_seed,
        "final_directive": final_directive,
        "event_graph": event_graph,
        "world_tick": world_tick_delta,
        "final_result": final_result,
    }
    try:
        path = turn_trace.persist_trace(turn_index, payload)
        return str(path)
    except OSError as exc:  # pragma: no cover - defensive
        LOGGER.warning("Unable to write turn trace: %s", exc)
        return None


def _extract_choice_id(
    choice_payload: Optional[Union[Dict[str, Any], str]],
) -> Optional[str]:
    if choice_payload is None:
        return None
    if isinstance(choice_payload, dict):
        for key in ("id", "choice_id", "option_id"):
            value = choice_payload.get(key)
            if value:
                return str(value)
        return None
    return str(choice_payload)


def _normalize_choice_payload(
    choice_payload: Optional[Union[Dict[str, Any], str]],
) -> Optional[Dict[str, Any]]:
    if choice_payload is None:
        return None
    if isinstance(choice_payload, dict):
        return dict(choice_payload)
    return {"id": str(choice_payload)}
