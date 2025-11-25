"""Test state store persistence and integrity."""

import pytest
import json
from pathlib import Path
from fortress_director.core.state_store import StateStore


@pytest.fixture
def state_store(tmp_path: Path) -> StateStore:
    """Create state store for testing."""
    return StateStore(tmp_path / "world_state.json")


def test_state_store_persistence(state_store: StateStore) -> None:
    """Test that state is persisted to disk correctly."""
    initial_state = state_store.snapshot()
    initial_turn = initial_state.get("turn", 0)

    # Modify and persist
    modified_state = initial_state.copy()
    modified_state["turn"] = initial_turn + 5
    state_store.persist(modified_state)

    # Load fresh store from same path
    fresh_store = StateStore(state_store._path)
    fresh_snapshot = fresh_store.snapshot()

    # Verify persisted state
    assert fresh_snapshot.get("turn") == initial_turn + 5


def test_state_store_json_format(state_store: StateStore) -> None:
    """Test that state is saved in valid JSON format."""
    state = state_store.snapshot()
    state["turn"] = 42
    state_store.persist(state)

    # Verify JSON is valid
    json_text = state_store._path.read_text(encoding="utf-8")
    loaded = json.loads(json_text)
    assert loaded.get("turn") == 42


def test_state_store_snapshot(state_store: StateStore) -> None:
    """Test snapshot creation."""
    snap = state_store.snapshot()

    assert isinstance(snap, dict)
    assert "turn" in snap
    assert isinstance(snap.get("turn"), int)


def test_state_store_mutation_isolation(state_store: StateStore) -> None:
    """Test that snapshots are independent copies."""
    snap1 = state_store.snapshot()
    snap1["turn"] = 999

    snap2 = state_store.snapshot()

    # Modify snap1 should not affect snap2
    assert snap2.get("turn") != 999
