"""Test StateArchive persistence layer (Phase 4)."""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from fortress_director.core.state_archive import StateArchive


@pytest.fixture
def temp_db():
    """Create a temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_archive():
    """Create a StateArchive with sample data."""
    archive = StateArchive("test_session_001")
    for turn in range(1, 21):
        state = {
            "world": {"threat_level": float(turn)},
            "npc_locations": [
                {
                    "id": f"npc_{i}",
                    "name": f"NPC {i}",
                    "morale": 80 - (turn * 2),
                    "fatigue": 10 + (turn * 2),
                    "x": 10 + turn,
                    "y": 20 + turn,
                }
                for i in range(1, 3)
            ],
            "recent_events": [f"Event {turn}"],
        }
        delta = {
            "recent_events": [f"Event {turn}"],
            "flags_added": ["flag_a", "flag_b"] if turn % 5 == 0 else [],
        }
        archive.record_turn(turn, state, delta)
    return archive


def test_archive_save_to_db(sample_archive, temp_db):
    """Test saving archive to database."""
    result = sample_archive.save_to_db(temp_db, turn_number=20)
    assert result is True

    # Verify database exists and has data
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Check metadata
    cursor.execute(
        "SELECT last_saved_turn FROM archive_metadata WHERE session_id = ?",
        ("test_session_001",),
    )
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == 20

    # Check current states saved
    cursor.execute(
        "SELECT COUNT(*) FROM archive_turns WHERE session_id = ? AND tier = ?",
        ("test_session_001", "current"),
    )
    count = cursor.fetchone()[0]
    assert count > 0

    # Check recent deltas saved
    cursor.execute(
        "SELECT COUNT(*) FROM archive_turns WHERE session_id = ? AND tier = ?",
        ("test_session_001", "recent"),
    )
    count = cursor.fetchone()[0]
    assert count > 0

    conn.close()


def test_archive_load_from_db(sample_archive, temp_db):
    """Test loading archive from database."""
    # Save
    sample_archive.save_to_db(temp_db, turn_number=20)

    # Load
    loaded = StateArchive.load_from_db(temp_db, "test_session_001")
    assert loaded is not None

    # Verify structure
    assert len(loaded.current_states) > 0
    assert len(loaded.recent_deltas) > 0
    assert len(loaded.threat_timeline) > 0
    assert len(loaded.npc_status_history) > 0


def test_archive_round_trip(sample_archive, temp_db):
    """Test save/load round trip preserves data."""
    original_count = len(sample_archive.current_states)
    original_threats = len(sample_archive.threat_timeline)
    original_npcs = len(sample_archive.npc_status_history)

    # Save and load
    sample_archive.save_to_db(temp_db, turn_number=20)
    loaded = StateArchive.load_from_db(temp_db, "test_session_001")

    # Verify preservation
    assert len(loaded.current_states) == original_count
    assert len(loaded.threat_timeline) == original_threats
    assert len(loaded.npc_status_history) == original_npcs

    # Verify specific values
    for turn, state in loaded.current_states.items():
        assert "world" in state
        assert "threat_level" in state["world"]


def test_archive_persistence_multiple_sessions(temp_db):
    """Test persistence for multiple sessions independently."""
    from fortress_director.core.state_archive import MAX_CURRENT_TURNS

    # Create session 1
    archive1 = StateArchive("session_1")
    for turn in range(1, 11):
        state = {"data": f"session1_turn{turn}"}
        archive1.record_turn(turn, state, {})

    # Create session 2
    archive2 = StateArchive("session_2")
    for turn in range(1, 16):
        state = {"data": f"session2_turn{turn}"}
        archive2.record_turn(turn, state, {})

    # Save both
    assert archive1.save_to_db(temp_db, 10)
    assert archive2.save_to_db(temp_db, 15)

    # Load independently
    loaded1 = StateArchive.load_from_db(temp_db, "session_1")
    loaded2 = StateArchive.load_from_db(temp_db, "session_2")

    # Verify sessions are isolated
    # Current states are only kept for recent turns
    assert len(loaded1.current_states) <= MAX_CURRENT_TURNS
    assert len(loaded2.current_states) <= MAX_CURRENT_TURNS
    # But deltas track additional history
    assert len(loaded1.current_states) + len(loaded1.recent_deltas) > 6
    assert len(loaded2.current_states) + len(loaded2.recent_deltas) > 6


def test_archive_persistence_json_serialization(sample_archive, temp_db):
    """Test that complex JSON structures survive serialization."""
    # Add complex state
    sample_archive.current_states[99] = {
        "world": {
            "threat_level": 9.9,
            "locations": [{"x": 1, "y": 2}, {"x": 3, "y": 4}],
            "metadata": {"key": "value", "nested": {"deep": True}},
        },
        "npc_locations": [
            {
                "id": "complex_npc",
                "inventory": ["item1", "item2"],
                "stats": {"hp": 100, "mp": 50},
            }
        ],
    }

    # Save and load
    sample_archive.save_to_db(temp_db, turn_number=99)
    loaded = StateArchive.load_from_db(temp_db, "test_session_001")

    # Verify complex structure
    assert 99 in loaded.current_states
    state = loaded.current_states[99]
    assert state["world"]["threat_level"] == 9.9
    assert len(state["world"]["locations"]) == 2
    assert state["world"]["metadata"]["nested"]["deep"] is True


def test_archive_persistence_handles_missing_db(temp_db):
    """Test graceful handling when database doesn't exist yet."""
    # Delete the database if it exists
    Path(temp_db).unlink(missing_ok=True)

    archive = StateArchive("test_session")
    for turn in range(1, 6):
        state = {"turn": turn}
        archive.record_turn(turn, state, {})

    # Save to non-existent DB (should create it)
    result = archive.save_to_db(temp_db, turn_number=5)
    assert result is True
    assert Path(temp_db).exists()


def test_archive_persistence_idempotent(sample_archive, temp_db):
    """Test that saving the same archive twice is idempotent."""
    # Save twice
    result1 = sample_archive.save_to_db(temp_db, turn_number=20)
    result2 = sample_archive.save_to_db(temp_db, turn_number=20)

    assert result1 is True
    assert result2 is True

    # Load and verify no duplicates
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) FROM archive_turns
        WHERE session_id = ? AND tier = 'current'
        """,
        ("test_session_001",),
    )
    count = cursor.fetchone()[0]
    expected = len(sample_archive.current_states)
    assert count == expected

    conn.close()


def test_archive_load_empty_session(temp_db):
    """Test loading archive from session with no data."""
    archive = StateArchive("empty_session")
    archive.save_to_db(temp_db, turn_number=0)

    loaded = StateArchive.load_from_db(temp_db, "empty_session")
    assert loaded is not None
    assert len(loaded.current_states) == 0
    assert len(loaded.threat_timeline) == 0


def test_archive_persistence_threat_timeline(sample_archive, temp_db):
    """Test threat timeline persistence."""
    original_threats = sample_archive.threat_timeline.copy()

    sample_archive.save_to_db(temp_db, turn_number=20)
    loaded = StateArchive.load_from_db(temp_db, "test_session_001")

    assert loaded.threat_timeline == original_threats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
