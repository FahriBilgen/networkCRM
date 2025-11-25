from __future__ import annotations

import json
from pathlib import Path

SCENARIO_PATH = Path(__file__).resolve().parents[2] / "scenario" / "demo_siege.json"


def test_demo_siege_has_five_turns_with_fallbacks() -> None:
    payload = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    assert payload["scenario_id"] == "demo_siege"
    turns = payload.get("turns") or []
    assert len(turns) == 5
    for idx, turn in enumerate(turns, start=1):
        assert turn.get("turn") == idx
        fallback = turn.get("fallback") or {}
        assert fallback.get("narrative")
        assert fallback.get("actions"), f"Turn {idx} missing fallback actions"
