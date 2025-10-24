"""Integration test for a full 10-turn run with real Ollama models."""

from __future__ import annotations
import json
import os
from pathlib import Path
import pytest

from fortress_director.orchestrator.orchestrator import Orchestrator, StateStore
from fortress_director.settings import DEFAULT_WORLD_STATE


@pytest.mark.integration
def test_full_run_10_turns(tmp_path: Path) -> None:
    """Run 10 turns with real Ollama models, validate outputs and artifacts."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip("Skipping real model test; set FORTRESS_USE_OLLAMA=1 to run")

    out_dir = tmp_path / "artifacts" / "full_run_10"
    out_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = Orchestrator.__new__(Orchestrator)
    from fortress_director.agents.event_agent import EventAgent
    from fortress_director.agents.world_agent import WorldAgent
    from fortress_director.agents.character_agent import CharacterAgent
    from fortress_director.agents.judge_agent import JudgeAgent
    from fortress_director.rules.rules_engine import RulesEngine
    from fortress_director.codeaware.function_registry import SafeFunctionRegistry
    from fortress_director.codeaware.function_validator import FunctionCallValidator
    from fortress_director.codeaware.rollback_system import RollbackSystem
    from fortress_director.utils.metrics_manager import MetricManager

    state_store = StateStore(out_dir / "world_state.json")
    orchestrator.state_store = state_store
    orchestrator.event_agent = EventAgent()
    orchestrator.world_agent = WorldAgent()
    orchestrator.character_agent = CharacterAgent()
    orchestrator.judge_agent = JudgeAgent()
    orchestrator.rules_engine = RulesEngine(judge_agent=orchestrator.judge_agent)
    orchestrator.function_registry = SafeFunctionRegistry()
    orchestrator.function_validator = FunctionCallValidator(
        orchestrator.function_registry, max_calls_per_function=10, max_total_calls=50
    )
    orchestrator.rollback_system = RollbackSystem(
        snapshot_provider=state_store.snapshot,
        restore_callback=state_store.persist,
        max_checkpoints=10,
    )
    orchestrator._register_default_safe_functions()

    baseline = dict(DEFAULT_WORLD_STATE)
    baseline["rng_seed"] = 12345
    baseline["turn"] = 0
    baseline["current_turn"] = 0
    MetricManager(baseline, log_sink=[])
    orchestrator.state_store.persist(baseline)

    major_events_triggered = False
    major_flag_set = False
    safe_functions_executed = False
    win_loss_values = []

    for turn in range(1, 11):
        try:
            result = orchestrator.run_turn()
            state = orchestrator.state_store.snapshot()

            assert "scene" in result
            assert "options" in result
            if result.get("win_loss", {}).get("status") in ["loss", "win"]:
                assert isinstance(result["options"], list)
            else:
                assert (
                    isinstance(result["options"], list)
                    and 1 <= len(result["options"]) <= 3
                )
            assert "character_reactions" in result
            assert "metrics_after" in result
            assert "world" in result
            assert "event" in result
            assert "win_loss" in result

            if result.get("event", {}).get("major_event"):
                major_events_triggered = True
            if any("major_" in flag for flag in state.get("flags", [])):
                major_flag_set = True

            if any(
                "change_weather" in str(effect) for effect in result.get("effects", [])
            ):
                safe_functions_executed = True
                assert state.get("world_constraint") != baseline.get("world_constraint")

                win_loss = result["win_loss"]
                assert "reason" in win_loss and win_loss["reason"].strip()

                win_loss_values.append(win_loss.get("status", "ongoing"))

                with open(
                    out_dir / f"turn_{turn:02d}.json", "w", encoding="utf-8"
                ) as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                with open(
                    out_dir / f"state_{turn:02d}.json", "w", encoding="utf-8"
                ) as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
                log_entry = {
                    "turn": turn,
                    "agent": "orchestrator",
                    "message": f"Turn {turn} completed",
                    "deltas": metrics,
                }
                with open(out_dir / "log.ndjson", "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Turn {turn} failed with exception: {e}")
            break

    assert major_events_triggered or major_flag_set
    assert safe_functions_executed
    assert all(status in ["ongoing", "win", "loss"] for status in win_loss_values)
    if win_loss_values:
        final_status = win_loss_values[-1]
        assert final_status in ["ongoing", "win", "loss"]
