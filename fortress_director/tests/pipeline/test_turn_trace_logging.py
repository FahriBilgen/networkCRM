from fortress_director.pipeline import turn_trace


def test_turn_trace_round_trip(tmp_path) -> None:
    monkey_dir = tmp_path / "traces"
    monkey_dir.mkdir()
    original_dir = turn_trace.TRACE_DIR
    turn_trace.TRACE_DIR = monkey_dir  # type: ignore[attr-defined]
    try:
        payload = {"turn": 7, "note": "demo"}
        path = turn_trace.persist_trace(7, payload)
        assert path.exists()
        loaded = turn_trace.load_trace(7)
        assert loaded["note"] == "demo"
        summaries = turn_trace.list_traces()
        assert any(entry["turn"] == 7 for entry in summaries)
    finally:
        turn_trace.TRACE_DIR = original_dir  # type: ignore[attr-defined]
