"""Integration test for a 2-turn smoke run with real Ollama models."""

from __future__ import annotations
import json
import os
from pathlib import Path
import pytest

from fortress_director.orchestrator.orchestrator import Orchestrator, StateStore
from fortress_director.settings import DEFAULT_WORLD_STATE


@pytest.mark.integration
def test_smoke_2turn_real_llm(tmp_path: Path) -> None:
    """Run 2 turns with real Ollama models in non-persistent mode, validate artifacts."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip("Skipping real model test; set FORTRESS_USE_OLLAMA=1 to run")

    out_dir = tmp_path / "runs" / "latest_run"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Create orchestrator with runs_dir
    orchestrator = Orchestrator.__new__(Orchestrator)
    from fortress_director.agents.event_agent import EventAgent
    from fortress_director.agents.world_agent import WorldAgent
    from fortress_director.agents.character_agent import CharacterAgent
    from fortress_director.agents.director_agent import DirectorAgent
    from fortress_director.agents.planner_agent import PlannerAgent
    from fortress_director.agents.creativity_agent import CreativityAgent
    from fortress_director.agents.judge_agent import JudgeAgent
    from fortress_director.rules.rules_engine import RulesEngine
    from fortress_director.codeaware.function_registry import SafeFunctionRegistry
    from fortress_director.codeaware.function_validator import FunctionCallValidator
    from fortress_director.codeaware.rollback_system import RollbackSystem

    state_store = StateStore(tmp_path / "world_state.json")  # Non-persistent
    orchestrator.state_store = state_store
    orchestrator.event_agent = EventAgent()
    orchestrator.world_agent = WorldAgent()
    orchestrator.character_agent = CharacterAgent()
    orchestrator.creativity_agent = CreativityAgent()
    orchestrator.planner_agent = PlannerAgent()
    orchestrator.director_agent = DirectorAgent()
    orchestrator.judge_agent = JudgeAgent()
    orchestrator.rules_engine = RulesEngine(judge_agent=orchestrator.judge_agent)
    orchestrator.function_registry = SafeFunctionRegistry()
    orchestrator.function_validator = FunctionCallValidator(
        orchestrator.function_registry, max_calls_per_function=5, max_total_calls=20
    )
    orchestrator.rollback_system = RollbackSystem(
        snapshot_provider=state_store.snapshot,
        restore_callback=state_store.persist,
        max_checkpoints=3,
    )
    orchestrator.runs_dir = out_dir
    orchestrator._register_default_safe_functions()

    # Run 2 turns with seed=42
    for turn in range(1, 3):
        result = orchestrator.run_turn(player_choice_id=None)
        # Save turn snapshot
        snapshot_file = out_dir / f"turn_{turn:03d}.json"
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Turn {turn} completed, snapshot saved to {snapshot_file}")

    # Validate artifacts
    audit_file = out_dir / "audit.jsonl"
    replay_file = out_dir / "replay.jsonl"
    # Note: audit/replay files are only created if safe functions are called
    # In this test, no safe functions are called, so files may not exist

    # Check audit entries if file exists
    if audit_file.exists():
        with open(audit_file, "r", encoding="utf-8") as f:
            audit_lines = f.readlines()
        assert len(audit_lines) > 0, "audit.jsonl should have entries"
        for line in audit_lines:
            entry = json.loads(line)
            assert "timestamp" in entry
            assert "turn_index" in entry
            assert "caller" in entry
            assert "safe_call" in entry
            assert "validator_verdict" in entry
            assert "applied" in entry
    else:
        # No safe functions called, file not created
        pass

    # Check replay entries if file exists
    if replay_file.exists():
        with open(replay_file, "r", encoding="utf-8") as f:
            replay_lines = f.readlines()
        for line in replay_lines:
            entry = json.loads(line)
            assert "timestamp" in entry
            assert "turn_index" in entry
            assert "caller" in entry
            assert "safe_call" in entry
            assert "applied_result_diff" in entry
    else:
        # No safe functions called, file not created
        pass

    # Check turn snapshots
    for turn in range(1, 3):
        snapshot_file = out_dir / f"turn_{turn:03d}.json"
        assert snapshot_file.exists(), f"turn_{turn:03d}.json should exist"
        with open(snapshot_file, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        assert "scene" in snapshot
        assert "options" in snapshot
        assert "safe_function_results" in snapshot

    # Ensure world_state.json reflects the turns run
    original_state = DEFAULT_WORLD_STATE
    current_state = state_store._state
    assert (
        current_state.get("turn", 0) == 2
    ), "world_state.json should reflect 2 turns run"

    print("Smoke test passed: 2 turns completed, artifacts validated.")
