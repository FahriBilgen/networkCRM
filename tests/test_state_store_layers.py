from __future__ import annotations

import json

from fortress_director.orchestrator.orchestrator import StateStore


def test_state_store_persist_emits_cold_refs(tmp_path):
    state_path = tmp_path / "world_state.json"
    store = StateStore(state_path)
    state = store.snapshot()
    state["turn"] = 1
    state["recent_events"] = [{"text": "alpha"}]
    store.persist(state)

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert "_cold_refs" in payload
    assert "recent_events" not in payload

    history_dir = state_path.parent / "history"
    history_files = sorted(history_dir.glob("turn_*.json"))
    assert history_files, "Cold diff file should exist"


def test_state_store_hydrates_cold_from_history(tmp_path):
    state_path = tmp_path / "world_state.json"
    store = StateStore(state_path)
    state = store.snapshot()
    state["turn"] = 2
    state["recent_events"] = ["alpha"]
    store.persist(state)

    reloaded = StateStore(state_path)
    snapshot = reloaded.snapshot()
    assert snapshot["recent_events"] == ["alpha"]


def test_snapshot_hot_returns_only_hot_layer(tmp_path):
    state_path = tmp_path / "world_state.json"
    store = StateStore(state_path)
    state = store.snapshot()
    state["turn"] = 3
    state["recent_events"] = ["beta"]
    store.persist(state)

    hot_snapshot = store.snapshot_hot()
    assert "recent_events" not in hot_snapshot
    assert "metrics" in hot_snapshot
