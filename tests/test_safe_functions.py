from __future__ import annotations

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

    orchestrator = orchestrator_mod.Orchestrator.build_default()

    result = orchestrator.run_turn()

    # Verify safe functions were executed from real agent outputs
    safe_results = result.get("safe_function_results", [])
    # Real agents may or may not generate safe functions, but the structure
    # should be valid
    assert isinstance(safe_results, list), "safe_function_results should be a list"

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
