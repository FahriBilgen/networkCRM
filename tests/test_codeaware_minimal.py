# Add fortress_director to sys.path for local test runs
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fortress_director.codeaware.function_registry import (
    SafeFunctionRegistry,
    FunctionCall,
)
from fortress_director.codeaware.function_validator import (
    FunctionCallValidator,
)
from fortress_director.codeaware.rollback_system import (
    RollbackSystem,
    RollbackSystemError,
)


def test_safe_function_registry_register_and_get():
    registry = SafeFunctionRegistry()

    def dummy():
        return 42

    registry.register("foo", dummy, validator=lambda call: call)
    entry = registry.get("foo")
    assert entry.function() == 42
    assert entry.name == "foo"


def test_safe_function_registry_duplicate():
    registry = SafeFunctionRegistry()
    registry.register("foo", lambda: None, validator=lambda call: call)
    with pytest.raises(Exception):
        registry.register("foo", lambda: None, validator=lambda call: call)


def test_function_call_validator_happy_path():
    registry = SafeFunctionRegistry()
    registry.register("foo", lambda: 1, validator=lambda call: call)
    validator = FunctionCallValidator(registry)
    call = validator.validate({"name": "foo"})
    assert isinstance(call, FunctionCall)
    assert call.name == "foo"


def test_function_call_validator_invalid():
    registry = SafeFunctionRegistry()
    validator = FunctionCallValidator(registry)
    with pytest.raises(Exception):
        validator.validate({"name": "bar"})


def test_rollback_system_happy_path():
    state = {"x": 1}

    def snapshot():
        return dict(state)

    def restore(s):
        state.clear()
        state.update(s)

    rs = RollbackSystem(snapshot, restore)
    rs.create_checkpoint()
    state["x"] = 2
    rs.rollback()
    assert state["x"] == 1


def test_rollback_system_no_checkpoint():
    state = {"x": 1}

    def snapshot():
        return dict(state)

    def restore(s):
        state.clear()
        state.update(s)

    rs = RollbackSystem(snapshot, restore)
    with pytest.raises(RollbackSystemError):
        rs.rollback()
