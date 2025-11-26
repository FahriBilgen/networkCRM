"""Test State Archive integration with API."""

import pytest
from fortress_director.core.state_archive import StateArchive


def test_archive_lifecycle():
    """Test that archive can be created and used in API context."""
    archive = StateArchive("session_123")

    # Record turns
    for i in range(1, 12):
        state = {"world": {"threat_level": float(i)}}
        delta = {"recent_events": [f"Event {i}"], "flags_added": [f"flag_{i}"]}
        archive.record_turn(i, state, delta)

    # Check state was recorded
    assert len(archive.current_states) > 0
    assert len(archive.threat_timeline) > 0


def test_archive_ready_for_injection():
    """Test that archive context is available for LLM prompt injection."""
    archive = StateArchive("session_456")

    # Record many turns
    for i in range(1, 20):
        state = {"world": {"threat_level": float(i)}}
        delta = {
            "recent_events": [f"Major event {i}"],
            "flags_added": ["flag"],
        }
        archive.record_turn(i, state, delta)

    # At turn 18, context should be ready
    context = archive.get_context_for_prompt(18)
    assert context is not None


def test_archive_memory_bounded():
    """Test that archive doesn't grow unbounded."""
    archive = StateArchive("session_789")

    # Record 100 turns
    for i in range(1, 101):
        state = {"world": {"threat_level": float(i % 10)}}
        delta = {"recent_events": [f"Event {i}" * 10]}
        archive.record_turn(i, state, delta)

    # Check memory is bounded
    size = archive.get_current_state_size()
    assert size < 10_000_000  # Should be less than 10MB


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
