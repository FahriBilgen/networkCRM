import pytest
from fortress_director.codeaware.function_registry import (
    SafeFunctionRegistry,
    FunctionValidationError,
)
from fortress_director.codeaware.function_validator import FunctionCallValidator
from fortress_director.codeaware.rollback_system import RollbackSystem
from fortress_director.orchestrator.orchestrator import Orchestrator, StateStore
from pathlib import Path
import tempfile
import shutil
import os


def test_invalid_safe_function_triggers_rollback_and_abort():
    # Setup temp state file
    temp_dir = tempfile.mkdtemp()
    state_path = Path(temp_dir) / "world_state.json"
    state_path.write_text('{"turn": 0, "current_room": "entrance", "metrics": {}}')
    state_store = StateStore(state_path)
    registry = SafeFunctionRegistry()
    validator = FunctionCallValidator(registry)
    rollback_system = RollbackSystem(state_store.snapshot, state_store.persist)

    # Minimal mock agent/rules objects
    class DummyAgent:
        def __getattr__(self, name):
            return lambda *a, **k: None

    class DummyRules:
        def __getattr__(self, name):
            return lambda *a, **k: None

    orchestrator = Orchestrator(
        state_store=state_store,
        function_validator=validator,
        rollback_system=rollback_system,
        runs_dir=temp_dir,
        event_agent=DummyAgent(),
        world_agent=DummyAgent(),
        creativity_agent=DummyAgent(),
        character_agent=DummyAgent(),
        judge_agent=DummyAgent(),
        rules_engine=DummyRules(),
        function_registry=registry,
    )
    # Simulate an event output with an invalid safe function
    event_output = {"safe_functions": ["spawn_item('undefined')"]}
    character_output = []
    # Should raise and rollback
    with pytest.raises(Exception) as excinfo:
        orchestrator._execute_safe_function_queue(
            event_output=event_output, character_output=character_output
        )
    assert "spawn_item requires item_id and target" in str(excinfo.value)
    shutil.rmtree(temp_dir)
