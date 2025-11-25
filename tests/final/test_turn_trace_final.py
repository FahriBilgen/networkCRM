from __future__ import annotations

import json
from pathlib import Path

from fortress_director.pipeline import turn_trace


def test_persist_trace_writes_final_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(turn_trace, "TRACE_DIR", Path(tmp_path))
    monkeypatch.setattr(turn_trace, "ensure_runtime_paths", lambda: None)

    final_result = {
        "final_path": {"id": "heroic_last_stand"},
        "npc_outcomes": [],
    }
    payload = {
        "turn": 30,
        "player_choice": None,
        "final_result": final_result,
    }
    turn_trace.persist_trace(30, payload)
    final_file = Path(tmp_path) / "turn_final.json"
    assert final_file.exists()
    data = json.loads(final_file.read_text(encoding="utf-8"))
    assert data["final_path"]["id"] == "heroic_last_stand"
