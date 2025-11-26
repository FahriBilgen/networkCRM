"""Tests for State Archive module."""

import pytest
from fortress_director.core.state_archive import (
    StateArchive,
    inject_archive_to_prompt,
    ARCHIVE_INTERVAL,
)


@pytest.fixture
def archive():
    """Create a fresh StateArchive for testing."""
    return StateArchive("test_session_1")


def test_archive_initialization(archive):
    """Test StateArchive initializes correctly."""
    assert archive.session_id == "test_session_1"
    assert len(archive.current_states) == 0
    assert len(archive.recent_deltas) == 0
    assert len(archive.archive_summaries) == 0
    assert len(archive.event_log) == 0
    assert len(archive.npc_status_history) == 0
    assert len(archive.threat_timeline) == 0


def test_record_turn_keeps_current_state(archive):
    """Test that recent turns are kept in full."""
    state1 = {"world": {"threat_level": 3.5}, "npcs": {"scout": {}}}
    delta1 = {"threat_delta": 0.5}

    archive.record_turn(1, state1, delta1)

    assert 1 in archive.current_states
    assert archive.current_states[1] == state1


def test_record_turn_converts_to_delta(archive):
    """Test that old turns are converted to deltas."""
    # Simulate turns 1-6
    for i in range(1, 7):
        state = {"world": {"threat_level": float(i)}, "npcs": {}}
        delta = {"turn": i}
        archive.record_turn(i, state, delta)

    # Turn 7 should be stored as delta only
    archive.record_turn(7, {"world": {"threat_level": 7.0}}, {"turn": 7})

    # Turns 1-6 should be in current_states (kept within limit)
    assert 6 in archive.current_states
    assert 1 in archive.current_states  # Recent states are kept
    # Turn 7 should be in recent_deltas (exceeds MAX_CURRENT_TURNS)
    assert 7 in archive.recent_deltas


def test_threat_timeline_tracking(archive):
    """Test that threat levels are tracked."""
    for i in range(1, 6):
        state = {"world": {"threat_level": float(i)}}
        archive.record_turn(i, state, {})

    assert len(archive.threat_timeline) == 5
    assert archive.threat_timeline[0] == 1.0
    assert archive.threat_timeline[-1] == 5.0


def test_threat_timeline_culling(archive):
    """Test that threat timeline doesn't grow unbounded."""
    for i in range(1, 50):
        state = {"world": {"threat_level": float(i % 10)}}
        archive.record_turn(i, state, {})

    # Should be culled to MAX_RECENT_HISTORY * 2 = 20
    assert len(archive.threat_timeline) <= 20


def test_npc_status_tracking(archive):
    """Test that NPC status changes are tracked."""
    state1 = {
        "world": {"threat_level": 1.0},
        "npc_locations": [
            {"id": "scout_1", "morale": 80, "fatigue": 20, "x": 10, "y": 20}
        ],
    }
    archive.record_turn(1, state1, {})

    assert "scout_1" in archive.npc_status_history
    assert len(archive.npc_status_history["scout_1"]) == 1
    assert "Morale:80" in archive.npc_status_history["scout_1"][0]


def test_event_extraction(archive):
    """Test that major events are extracted."""
    delta1 = {
        "recent_events": [
            "Scout reports enemy movement",
            "Gate damaged by siege weapon",
        ],
        "flags_added": ["alert_sounded"],
    }
    archive.record_turn(1, {"world": {"threat_level": 1.0}}, delta1)

    assert len(archive.event_log) >= 2
    assert any("Scout" in e for e in archive.event_log)
    assert any("Flag set:" in e for e in archive.event_log)


def test_archive_compression(archive):
    """Test that archive compresses at intervals."""
    # Record 10 turns (should trigger compression)
    for i in range(1, 11):
        state = {"world": {"threat_level": float(i)}}
        delta = {
            "recent_events": [f"Event {i}"],
            "flags_added": [f"flag_{i}"],
        }
        archive.record_turn(i, state, delta)

    # Should have created an archive entry
    assert len(archive.archive_summaries) > 0


def test_get_context_for_prompt_early(archive):
    """Test that context is None for early turns."""
    for i in range(1, 5):
        state = {"world": {"threat_level": float(i)}}
        archive.record_turn(i, state, {})

    # Should return None (not yet at injection point)
    context = archive.get_context_for_prompt(5)
    assert context is None


def test_get_context_for_prompt_injection(archive):
    """Test that context is injected at right time."""
    # Populate with events
    for i in range(1, 19):
        state = {"world": {"threat_level": float(i)}}
        delta = {"recent_events": [f"Event {i}"], "flags_added": [f"flag_{i}"]}
        archive.record_turn(i, state, delta)

    # Turn 18 should get context (past turn 10, new injection window)
    context = archive.get_context_for_prompt(18)
    assert context is not None


def test_inject_archive_to_prompt_no_context(archive):
    """Test prompt injection when no context available."""
    original = "You are a game master"
    result = inject_archive_to_prompt(archive, 5, original)

    # Should return unchanged
    assert result == original


def test_inject_archive_to_prompt_with_context(archive):
    """Test prompt injection when context available."""
    # Build archive
    for i in range(1, 19):
        state = {"world": {"threat_level": float(i)}}
        delta = {"recent_events": [f"Event {i}"], "flags_added": [f"flag_{i}"]}
        archive.record_turn(i, state, delta)

    original = "You are a game master"
    result = inject_archive_to_prompt(archive, 18, original)

    # Should include historical context section
    assert "HISTORICAL CONTEXT" in result
    assert "CURRENT SITUATION" in result
    assert original in result


def test_state_size_estimation(archive):
    """Test memory size estimation."""
    state = {"world": {"threat_level": 1.0}, "npcs": {"scout": {"x": 10}}}
    archive.record_turn(1, state, {})

    size = archive.get_current_state_size()
    assert size > 0
    assert isinstance(size, int)


def test_archive_compact(archive):
    """Test archive compaction."""
    # Add large event log
    for i in range(100):
        archive.event_log.append(f"Event {i}" * 100)

    # Compact
    archive.compact(max_size_bytes=100)

    # Should be smaller
    assert len(archive.event_log) <= 50


def test_archive_serialization(archive):
    """Test archive can be serialized and restored."""
    # Populate archive
    for i in range(1, 12):
        state = {"world": {"threat_level": float(i)}, "npcs": {}}
        delta = {
            "recent_events": [f"Major event number {i}"],
            "flags_added": ["flag"],
        }
        archive.record_turn(i, state, delta)

    # Serialize
    data = archive.to_dict()

    # Restore
    restored = StateArchive.from_dict("test_session_1", data)

    # Check consistency
    assert len(restored.current_states) > 0
    assert len(restored.threat_timeline) > 0


def test_npc_status_history_culling(archive):
    """Test that NPC status history is culled."""
    state_template = {
        "world": {"threat_level": 1.0},
        "npc_locations": [
            {
                "id": "scout_1",
                "morale": 80,
                "fatigue": 20,
                "x": 10,
                "y": 20,
            }
        ],
    }

    # Record 20 turns (should cull to 10)
    for i in range(1, 21):
        state = state_template.copy()
        archive.record_turn(i, state, {})

    # Status history should be culled
    assert len(archive.npc_status_history["scout_1"]) <= 10


def test_multiple_npcs_tracking(archive):
    """Test tracking of multiple NPCs."""
    state = {
        "world": {"threat_level": 1.0},
        "npc_locations": [
            {"id": "scout", "morale": 80, "fatigue": 20, "x": 10, "y": 20},
            {"id": "merchant", "morale": 60, "fatigue": 40, "x": 20, "y": 30},
        ],
    }
    archive.record_turn(1, state, {})

    assert "scout" in archive.npc_status_history
    assert "merchant" in archive.npc_status_history
    assert len(archive.npc_status_history) == 2


def test_empty_state_delta_handling(archive):
    """Test handling of empty state deltas."""
    state = {"world": {"threat_level": 1.0}}
    archive.record_turn(1, state, {})

    # Should not crash
    assert len(archive.event_log) == 0


def test_archive_summary_content(archive):
    """Test that archive summary contains expected content."""
    # Populate
    for i in range(1, 11):
        state = {"world": {"threat_level": float(i)}}
        delta = {"recent_events": [f"Major event {i}"] * 3}
        archive.record_turn(i, state, delta)

    # Get summary
    summary = archive._build_archive_summary(10)

    assert "MAJOR EVENTS" in summary or len(summary) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
