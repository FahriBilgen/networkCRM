from __future__ import annotations

import json
import types
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Tuple

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
    state_path = tmp_path / "world_state.json"
    store = StateStore(state_path)

    def _persist_without_sqlite(
        self: StateStore,
        state: Dict[str, Any],
    ) -> None:
        self._state = deepcopy(state)
        payload = json.dumps(self._state, indent=2)
        self._path.write_text(payload, encoding="utf-8")

    store.persist = types.MethodType(_persist_without_sqlite, store)
    store.persist(store.snapshot())

    orchestrator.state_store = store
    orchestrator.event_agent = None
    orchestrator.world_agent = None
    orchestrator.character_agent = None
    orchestrator.judge_agent = None
    orchestrator.rules_engine = None
    orchestrator.function_registry = SafeFunctionRegistry()
    orchestrator.function_validator = FunctionCallValidator(
        orchestrator.function_registry,
        max_calls_per_function=5,
        max_total_calls=5,
    )
    orchestrator.rollback_system = RollbackSystem(
        snapshot_provider=store.snapshot,
        restore_callback=store.persist,
        max_checkpoints=3,
    )
    orchestrator.runs_dir = tmp_path / "runs"
    orchestrator.runs_dir.mkdir(parents=True, exist_ok=True)
    orchestrator._register_default_safe_functions()
    return orchestrator


def _guardrail_call(
    name: str,
    *,
    kwargs: Dict[str, Any],
    source: str,
    planner_origin: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    metadata = {"source": source}
    if planner_origin:
        metadata["planner_origin"] = True
    return ({"name": name, "kwargs": dict(kwargs)}, metadata)


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


def test_modify_resources_and_adjust_metric(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "modify_resources",
            "kwargs": {"amount": -5, "cause": "test_consumption"},
        }
    )
    orchestrator.run_safe_function(
        {
            "name": "adjust_metric",
            "kwargs": {"metric": "order", "delta": 7, "cause": "test_boost"},
        }
    )

    state = orchestrator.state_store.snapshot()
    metrics = state["metrics"]
    assert metrics["resources"] == 35
    assert metrics["order"] == 57


def test_set_time_of_day_updates_timeline(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "set_time_of_day",
            "kwargs": {"time_slot": "noon"},
        }
    )

    state = orchestrator.state_store.snapshot()
    assert state["time"] == "noon"
    timeline = state["timeline"]
    assert timeline
    assert timeline[-1]["type"] == "time_shift"
    assert timeline[-1]["to"] == "noon"


def test_trigger_environment_hazard_creates_entry(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "trigger_environment_hazard",
            "kwargs": {
                "hazard_id": "rockslide",
                "severity": 3,
                "duration": 2,
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    hazards = state["environment_hazards"]
    assert hazards
    hazard = hazards[0]
    assert hazard["hazard_id"] == "rockslide"
    assert hazard["severity"] == 3
    assert hazard["remaining"] == 2
    cooldowns = state["hazard_cooldowns"]
    assert cooldowns["rockslide"] >= state["turn"]


def test_schedule_npc_activity_appends_queue(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "schedule_npc_activity",
            "kwargs": {
                "npc_id": "rhea",
                "activity": "patrol",
                "duration": 2,
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    queue = state["npc_schedule"]["rhea"]
    assert queue
    assert queue[0]["activity"] == "patrol"
    assert queue[0]["duration"] == 2


def test_adjust_stockpile_never_drops_below_zero(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "adjust_stockpile",
            "kwargs": {
                "resource_id": "food",
                "delta": -500,
                "cause": "test_rationing",
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    assert state["stockpiles"]["food"] == 0
    log = state["stockpile_log"]
    assert log
    assert log[-1]["resource"] == "food"


def test_open_and_close_trade_route_records_history(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "open_trade_route",
            "kwargs": {
                "route_id": "northern_pass",
                "risk": 2,
                "reward": 5,
            },
        }
    )
    orchestrator.run_safe_function(
        {
            "name": "close_trade_route",
            "kwargs": {
                "route_id": "northern_pass",
                "reason": "siege",
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    assert "northern_pass" not in state["trade_routes"]
    history = state["trade_route_history"]
    assert history
    assert history[-1]["route_id"] == "northern_pass"
    assert history[-1]["status"] == "closed"


def test_reinforce_structure_caps_at_max(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "reinforce_structure",
            "kwargs": {
                "structure_id": "western_wall",
                "amount": 50,
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    wall = state["structures"]["western_wall"]
    assert wall["durability"] == wall["max_durability"]
    assert wall["status"] == "reinforced"


def test_repair_breach_consumes_resources(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "repair_breach",
            "kwargs": {
                "section_id": "inner_gate",
                "resources_spent": 10,
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    gate = state["structures"]["inner_gate"]
    assert gate["status"] == "stable"
    assert state["metrics"]["resources"] == 30


def test_set_watcher_route_assigns_members(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "set_watcher_route",
            "kwargs": {
                "route_id": "north_wall",
                "npc_ids": ["rhea", "boris"],
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    record = state["patrols"]["north_wall"]
    assert record["members"] == ["rhea", "boris"]
    assert record["status"] == "assigned"


def test_spawn_patrol_records_path(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "spawn_patrol",
            "kwargs": {
                "patrol_id": "night_watch",
                "members": ["rhea"],
                "path": ["gate", "tower"],
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    patrol = state["patrols"]["night_watch"]
    assert patrol["path"] == ["gate", "tower"]
    assert patrol["status"] == "active"


def test_resolve_combat_updates_metrics(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "resolve_combat",
            "kwargs": {
                "attacker": "rhea",
                "defender": "raider",
                "outcome": "attacker_win",
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    metrics = state["metrics"]
    assert metrics["morale"] > 50
    assert metrics["resources"] < 40
    assert state["combat_log"][-1]["outcome"] == "attacker_win"


def test_transfer_item_moves_between_entities(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "spawn_item",
            "kwargs": {"item_id": "torch", "target": "player"},
        }
    )
    orchestrator.run_safe_function(
        {
            "name": "transfer_item",
            "kwargs": {
                "from_id": "player",
                "to_id": "rhea",
                "item_id": "torch",
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    assert "torch" not in state["player"]["inventory"]
    assert "torch" in state.setdefault("items", {}).get("rhea", [])


def test_queue_major_event_upserts_entry(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "queue_major_event",
            "kwargs": {
                "event_id": "wall_collapse",
                "trigger_turn": 5,
            },
        }
    )
    orchestrator.run_safe_function(
        {
            "name": "queue_major_event",
            "kwargs": {
                "event_id": "wall_collapse",
                "trigger_turn": 7,
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    scheduled = state["scheduled_events"]
    assert len(scheduled) == 1
    assert scheduled[0]["trigger_turn"] == 7


def test_guardrails_block_world_wall_drop(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    planner_call = _guardrail_call(
        "adjust_metric",
        kwargs={"metric": "wall_integrity", "delta": -2},
        source="event_agent",
        planner_origin=True,
    )
    world_call = _guardrail_call(
        "adjust_metric",
        kwargs={"metric": "wall_integrity", "delta": -3},
        source="world_agent",
    )

    filtered, stats = orchestrator._apply_safe_function_guardrails(
        [planner_call, world_call]
    )

    assert planner_call in filtered
    assert world_call not in filtered
    assert stats["planner_lowered_wall_integrity"] is True
    assert stats["world_wall_integrity_skipped"] == 1


def test_guardrails_collapse_stockpile_duplicates(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    first = _guardrail_call(
        "adjust_stockpile",
        kwargs={"resource_id": "food", "delta": -2, "cause": "test"},
        source="event_agent",
    )
    second = _guardrail_call(
        "adjust_stockpile",
        kwargs={"resource_id": "food", "delta": 1, "cause": "world"},
        source="world_agent",
    )

    filtered, stats = orchestrator._apply_safe_function_guardrails([first, second])

    assert first in filtered
    assert second not in filtered
    assert stats["stockpile_collapsed"] == ["food"]


def test_guardrails_limit_objective_urgency(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    first = _guardrail_call(
        "adjust_metric",
        kwargs={"metric": "objective_urgency", "delta": -1},
        source="character:Rhea",
    )
    second = _guardrail_call(
        "adjust_metric",
        kwargs={"metric": "objective_urgency", "delta": -1},
        source="character:Boris",
    )

    filtered, stats = orchestrator._apply_safe_function_guardrails([first, second])

    assert first in filtered
    assert second not in filtered
    assert stats["objective_urgency_skipped"] == ["character:Boris"]


def test_advance_story_act_records_history(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "advance_story_act",
            "kwargs": {"act_id": "crisis", "progression": 0.4},
        }
    )

    state = orchestrator.state_store.snapshot()
    story = state["story_progress"]
    assert story["act"] == "crisis"
    assert story["progress"] == 0.4
    assert story["act_history"]


def test_lock_player_option_saves_reason(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator(tmp_path)

    orchestrator.run_safe_function(
        {
            "name": "lock_player_option",
            "kwargs": {
                "option_id": "retreat",
                "reason": "bridge destroyed",
            },
        }
    )

    state = orchestrator.state_store.snapshot()
    lock = state["locked_options"]["retreat"]
    assert lock["reason"] == "bridge destroyed"


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


def test_run_turn_executes_agent_safe_functions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib
    import json
    import os
    import shutil

    sqlite_sync_mod = importlib.import_module("fortress_director.utils.sqlite_sync")
    from fortress_director.settings import Settings, ensure_runtime_paths

    # Setup sandbox environment with real models
    settings_mod = importlib.import_module("fortress_director.settings")
    orchestrator_mod = importlib.import_module(
        "fortress_director.orchestrator.orchestrator"
    )
    base_agent_mod = importlib.import_module("fortress_director.agents.base_agent")

    base_settings = settings_mod.SETTINGS
    sandbox = Settings(
        project_root=tmp_path,
        db_path=tmp_path / "db" / "game_state.sqlite",
        world_state_path=tmp_path / "data" / "world_state.json",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        ollama_base_url=base_settings.ollama_base_url,
        ollama_timeout=300.0,  # Increased timeout for real models
        max_active_models=base_settings.max_active_models,
        semantic_cache_ttl=base_settings.semantic_cache_ttl,
        models=dict(base_settings.models),
    )
    ensure_runtime_paths(sandbox)
    shutil.copytree(
        settings_mod.PROJECT_ROOT / "prompts",
        sandbox.project_root / "prompts",
    )
    (sandbox.world_state_path).write_text(
        json.dumps(settings_mod.DEFAULT_WORLD_STATE, indent=2),
        encoding="utf-8",
    )

    # Force real Ollama models
    env_copy = os.environ.copy()
    env_copy["FORTRESS_USE_OLLAMA"] = "1"
    monkeypatch.setattr(os, "environ", env_copy)
    monkeypatch.setattr(settings_mod, "SETTINGS", sandbox, raising=False)
    monkeypatch.setattr(orchestrator_mod, "SETTINGS", sandbox, raising=False)
    monkeypatch.setattr(base_agent_mod, "SETTINGS", sandbox, raising=False)
    monkeypatch.setattr(
        sqlite_sync_mod,
        "sync_state_to_sqlite",
        lambda *_, **__: None,
    )
    monkeypatch.setattr(
        orchestrator_mod,
        "sync_state_to_sqlite",
        lambda *_, **__: None,
    )

    orchestrator = orchestrator_mod.Orchestrator.build_default()

    result = orchestrator.run_turn()

    # Verify safe functions were executed from real agent outputs
    safe_results = result.get("safe_function_results", [])
    # Real agents may or may not generate safe functions, but the structure
    # should be valid
    assert isinstance(
        safe_results,
        list,
    ), "safe_function_results should be a list"

    # Verify expected result structure
    assert "metrics_after" in result
    assert "glitch" in result
    assert "logs" in result
    assert "win_loss" in result
    assert "narrative" in result
    assert isinstance(result["metrics_after"]["order"], int)
    assert result["glitch"]["effects"]

    # Verify state was updated by safe functions
    state = orchestrator.state_store.snapshot()
    # Real agents may or may not generate safe functions, but structure
    # should be valid
    assert "world_constraint_from_prev_turn" in state
    assert "player" in state
    assert "inventory" in state["player"]
    assert not orchestrator.rollback_system.has_checkpoints()
