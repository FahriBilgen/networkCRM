from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import pytest

from fortress_director.codeaware.function_registry import (
    FunctionCall,
    FunctionValidationError,
    SafeFunctionRegistry,
)
from fortress_director.codeaware.function_validator import (
    FunctionCallValidator,
)
from fortress_director.codeaware.rollback_system import RollbackSystem
from fortress_director.orchestrator.orchestrator import (
    Orchestrator,
    StateStore,
)


def _make_orchestrator(tmp_path: Path) -> Orchestrator:
    orchestrator = Orchestrator.__new__(Orchestrator)
    store = StateStore(tmp_path / "world_state.json")
    orchestrator.state_store = store
    orchestrator.event_agent = None
    orchestrator.world_agent = None
    orchestrator.character_agent = None
    orchestrator.judge_agent = None
    orchestrator.rules_engine = None
    orchestrator.function_registry = SafeFunctionRegistry()
    orchestrator.function_validator = FunctionCallValidator(
        orchestrator.function_registry,
        max_calls_per_function=1,
        max_total_calls=5,
    )
    orchestrator.rollback_system = RollbackSystem(
        snapshot_provider=store.snapshot,
        restore_callback=store.persist,
        max_checkpoints=3,
    )
    orchestrator._register_default_safe_functions()
    return orchestrator


def test_change_weather_updates_world_constraint(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    result = orchestrator.run_safe_function(
        {
            "name": "change_weather",
            "kwargs": {
                "atmosphere": "storm clouds gather",
                "sensory_details": "rain lashes the parapets",
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    constraint = state["world_constraint_from_prev_turn"]
    assert constraint["atmosphere"] == "storm clouds gather"
    assert constraint["sensory_details"] == "rain lashes the parapets"
    assert result == {
        "atmosphere": "storm clouds gather",
        "sensory_details": "rain lashes the parapets",
    }


def test_spawn_item_targets_player_inventory(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "spawn_item",
            "kwargs": {"item_id": "quiver", "target": "player"},
        }
    )

    state = orchestrator.state_store.snapshot()
    assert "quiver" in state["player"]["inventory"]


def test_spawn_item_targets_location(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "spawn_item",
            "kwargs": {"item_id": "ballista", "target": "tower_east"},
        }
    )

    state = orchestrator.state_store.snapshot()
    assert state["items"]["tower_east"] == ["ballista"]


def test_move_npc_tracks_location(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "move_npc",
            "kwargs": {"npc_id": "rhea", "location": "wall_tower"},
        }
    )

    state = orchestrator.state_store.snapshot()
    assert state["npc_locations"]["rhea"] == "wall_tower"


def test_safe_function_failure_rolls_back_state(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    def _boom_validator(call: FunctionCall) -> FunctionCall:
        if call.args or call.kwargs:
            raise FunctionValidationError("boom expects no arguments")
        return call

    def _boom_function() -> Dict[str, Any]:
        state = orchestrator.state_store.snapshot()
        state.setdefault("metrics", {})["risk_applied_total"] = 999
        orchestrator.state_store.persist(state)
        raise RuntimeError("boom")

    orchestrator.register_safe_function(
        "boom",
        _boom_function,
        validator=_boom_validator,
    )

    before = orchestrator.state_store.snapshot()

    with pytest.raises(RuntimeError):
        orchestrator.run_safe_function({"name": "boom", "kwargs": {}})

    after = orchestrator.state_store.snapshot()
    assert (
        after["metrics"]["risk_applied_total"]
        == before["metrics"]["risk_applied_total"]
    )
    assert not orchestrator.rollback_system.has_checkpoints()

    with pytest.raises(RuntimeError):
        orchestrator.run_safe_function({"name": "boom", "kwargs": {}})


def test_run_turn_executes_agent_safe_functions(tmp_path: Path) -> None:
    class StubWorldAgent:
        def describe(self, _request: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "atmosphere": "mist",
                "sensory_details": "quiet",
            }

    class StubEventAgent:
        def generate(self, _request: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "scene": "Sparks on the parapet.",
                "options": [
                    {
                        "id": "opt_1",
                        "text": "Coordinate the archers",
                        "action_type": "talk",
                    }
                ],
                "major_event": False,
                "safe_functions": [
                    {
                        "name": "change_weather",
                        "kwargs": {
                            "atmosphere": "storm glare",
                            "sensory_details": "hail rattles the stones",
                        },
                        "metadata": {"origin": "event"},
                    }
                ],
            }

    class StubCharacterAgent:
        def react(self, _request: Dict[str, Any]) -> list[Dict[str, Any]]:
            return [
                {
                    "name": "Rhea",
                    "intent": "support",
                    "action": "brace",
                    "speech": "Bolstering the western tower!",
                    "effects": {},
                    "safe_functions": [
                        {
                            "name": "spawn_item",
                            "kwargs": {
                                "item_id": "bolt_crate",
                                "target": "player",
                            },
                            "metadata": {"origin": "character"},
                        }
                    ],
                }
            ]

    class StubRulesEngine:
        def process(
            self,
            *,
            state: Dict[str, Any],
            character_events: list[Dict[str, Any]],
            world_context: str,
            scene: str,
            player_choice: Dict[str, Any],
        ) -> Dict[str, Any]:
            _ = (character_events, world_context, scene, player_choice)
            return deepcopy(state)

    orchestrator = Orchestrator.__new__(Orchestrator)
    store = StateStore(tmp_path / "world_state.json")
    orchestrator.state_store = store
    orchestrator.event_agent = StubEventAgent()
    orchestrator.world_agent = StubWorldAgent()
    orchestrator.character_agent = StubCharacterAgent()
    orchestrator.judge_agent = None
    orchestrator.rules_engine = StubRulesEngine()
    orchestrator.function_registry = SafeFunctionRegistry()
    orchestrator.function_validator = FunctionCallValidator(
        orchestrator.function_registry,
        max_calls_per_function=5,
        max_total_calls=10,
    )
    orchestrator.rollback_system = RollbackSystem(
        snapshot_provider=store.snapshot,
        restore_callback=store.persist,
        max_checkpoints=5,
    )
    orchestrator._register_default_safe_functions()

    result = orchestrator.run_turn()

    safe_results = result.get("safe_function_results", [])
    assert {entry["name"] for entry in safe_results} == {
        "change_weather",
        "spawn_item",
    }

    state = orchestrator.state_store.snapshot()
    constraint = state["world_constraint_from_prev_turn"]
    assert constraint["atmosphere"] == "storm glare"
    assert constraint["sensory_details"] == "hail rattles the stones"
    assert "bolt_crate" in state["player"]["inventory"]
    assert not orchestrator.rollback_system.has_checkpoints()
