"""Tests for session persistence to database."""

import tempfile
from pathlib import Path

import pytest

from fortress_director.db.session_store import SessionStore


class TestSessionStore:
    """Test SessionStore database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary test database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_sessions.db"

            # Create minimal tables for testing
            import sqlite3

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    theme_id TEXT NOT NULL
                )
                """
            )
            conn.commit()
            conn.close()

            yield str(db_path)

    def test_session_store_records_session(self, temp_db):
        """SessionStore should record session to database."""
        store = SessionStore(db_path=temp_db)

        store.record_session("test_session_1", "siege_default")

        retrieved = store.get_session("test_session_1")
        assert retrieved is not None
        assert retrieved["session_id"] == "test_session_1"
        assert retrieved["theme_id"] == "siege_default"

    def test_session_store_retrieves_session(self, temp_db):
        """SessionStore should retrieve existing session."""
        store = SessionStore(db_path=temp_db)

        store.record_session("test_session_2", "orbital_outpost")

        retrieved = store.get_session("test_session_2")
        assert retrieved["session_id"] == "test_session_2"
        assert retrieved["theme_id"] == "orbital_outpost"

    def test_session_store_returns_none_for_missing(self, temp_db):
        """SessionStore should return None for missing session."""
        store = SessionStore(db_path=temp_db)

        retrieved = store.get_session("nonexistent_session")
        assert retrieved is None

    def test_session_store_lists_sessions(self, temp_db):
        """SessionStore should list recent sessions."""
        store = SessionStore(db_path=temp_db)

        store.record_session("session_a", "siege_default")
        store.record_session("session_b", "orbital_outpost")
        store.record_session("session_c", "siege_default")

        sessions = store.list_sessions()
        assert len(sessions) == 3
        session_ids = [s["session_id"] for s in sessions]
        assert "session_a" in session_ids
        assert "session_b" in session_ids
        assert "session_c" in session_ids

    def test_session_store_deletes_session(self, temp_db):
        """SessionStore should delete session from database."""
        store = SessionStore(db_path=temp_db)

        store.record_session("test_session_del", "siege_default")
        assert store.get_session("test_session_del") is not None

        store.delete_session("test_session_del")
        assert store.get_session("test_session_del") is None

    def test_session_store_ignores_duplicate_inserts(self, temp_db):
        """SessionStore should ignore duplicate session IDs."""
        store = SessionStore(db_path=temp_db)

        store.record_session("dup_session", "siege_default")
        store.record_session("dup_session", "orbital_outpost")

        retrieved = store.get_session("dup_session")
        assert retrieved["session_id"] == "dup_session"
        # Should keep first theme (not updated to second)
        assert retrieved["theme_id"] == "siege_default"

    def test_session_store_limit_list(self, temp_db):
        """SessionStore list should respect limit parameter."""
        store = SessionStore(db_path=temp_db)

        for i in range(5):
            store.record_session(f"session_{i}", "siege_default")

        sessions = store.list_sessions(limit=3)
        assert len(sessions) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
