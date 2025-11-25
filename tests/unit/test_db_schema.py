"""Unit tests for database schema validation and correctness."""

import sqlite3
import tempfile
from pathlib import Path
from typing import List, Tuple

import pytest


def load_schema(schema_path: Path) -> str:
    """Load SQL schema from file."""
    with open(schema_path, "r") as f:
        return f.read()


def get_table_names(conn: sqlite3.Connection) -> List[str]:
    """Get all user-defined table names from database."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return [row[0] for row in cursor.fetchall()]


def get_table_columns(
    conn: sqlite3.Connection, table_name: str
) -> List[Tuple[str, str]]:
    """Get columns and types for a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [(row[1], row[2]) for row in cursor.fetchall()]


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def schema_path():
    """Get path to schema.sql file."""
    root = Path(__file__).parent.parent.parent
    schema_file = root / "fortress_director" / "db" / "schema.sql"
    return schema_file


class TestSchemaExistence:
    """Test that schema.sql file exists and is not empty."""

    def test_schema_file_exists(self, schema_path):
        """Schema file should exist."""
        assert schema_path.exists(), f"Schema file not found at {schema_path}"

    def test_schema_file_not_empty(self, schema_path):
        """Schema file should have content (not 0 bytes)."""
        size = schema_path.stat().st_size
        assert size > 0, f"Schema file is empty (0 bytes): {schema_path}"
        assert size > 100, f"Schema file too small ({size} bytes), likely incomplete"


class TestSchemaValidity:
    """Test that schema.sql is valid SQL."""

    def test_schema_loads_without_error(self, schema_path, temp_db):
        """Schema should load and execute without SQL errors."""
        schema = load_schema(schema_path)
        conn = sqlite3.connect(temp_db)
        try:
            conn.executescript(schema)
            conn.commit()
        except sqlite3.DatabaseError as e:
            pytest.fail(f"Schema has SQL errors: {e}")
        finally:
            conn.close()


class TestSchemaTables:
    """Test that all required tables are created."""

    REQUIRED_TABLES = [
        "sessions",
        "game_turns",
        "checkpoints",
        "safe_function_calls",
        "audit_log",
        "metrics",
        "npc_state",
        "npc_states",
        "metadata",
        "schema_version",
    ]

    @pytest.fixture(autouse=True)
    def setup_db(self, schema_path, temp_db):
        """Create database with schema."""
        schema = load_schema(schema_path)
        self.conn = sqlite3.connect(temp_db)
        self.conn.executescript(schema)
        self.conn.commit()
        yield
        self.conn.close()

    def test_all_required_tables_created(self):
        """All required tables should exist."""
        tables = get_table_names(self.conn)
        for required in self.REQUIRED_TABLES:
            assert required in tables, f"Required table '{required}' not created"

    def test_sessions_table_structure(self):
        """Sessions table should have required columns."""
        columns = dict(get_table_columns(self.conn, "sessions"))
        assert "id" in columns
        assert "player_name" in columns
        assert "theme_id" in columns
        assert "status" in columns
        assert "created_at" in columns

    def test_game_turns_table_structure(self):
        """Game_turns table should have required columns."""
        columns = dict(get_table_columns(self.conn, "game_turns"))
        assert "id" in columns
        assert "session_id" in columns
        assert "turn_number" in columns
        assert "state_snapshot" in columns
        assert "player_choice_id" in columns

    def test_checkpoints_table_structure(self):
        """Checkpoints table should have required columns."""
        columns = dict(get_table_columns(self.conn, "checkpoints"))
        assert "id" in columns
        assert "session_id" in columns
        assert "turn_number" in columns
        assert "state" in columns
        assert "reason" in columns

    def test_safe_function_calls_table_structure(self):
        """Safe_function_calls table should have required columns."""
        columns = dict(get_table_columns(self.conn, "safe_function_calls"))
        assert "id" in columns
        assert "session_id" in columns
        assert "turn_number" in columns
        assert "function_name" in columns
        assert "success" in columns


class TestSchemaConstraints:
    """Test that schema constraints are properly defined."""

    @pytest.fixture(autouse=True)
    def setup_db(self, schema_path, temp_db):
        """Create database with schema."""
        schema = load_schema(schema_path)
        self.conn = sqlite3.connect(temp_db)
        self.conn.executescript(schema)
        self.conn.commit()
        yield
        self.conn.close()

    def test_foreign_keys_enforced(self):
        """Foreign key constraints should exist."""
        cursor = self.conn.cursor()

        # Check game_turns has foreign key to sessions
        cursor.execute("PRAGMA foreign_key_list(game_turns)")
        fk_rows = cursor.fetchall()
        assert len(fk_rows) > 0, "game_turns should have foreign key constraints"

    def test_unique_constraints_exist(self):
        """Unique constraints should be defined where needed."""
        cursor = self.conn.cursor()

        # Sessions.id should be unique (PRIMARY KEY)
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        sessions_def = cursor.fetchone()[0]
        assert "PRIMARY KEY" in sessions_def.upper()

    def test_insert_into_sessions_succeeds(self):
        """Should be able to insert into sessions table."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions (id, player_name, theme_id, status)
            VALUES (?, ?, ?, ?)
            """,
            ("test_session_1", "Alice", "siege_default", "active"),
        )
        self.conn.commit()

        # Verify insert
        cursor.execute("SELECT * FROM sessions WHERE id = ?", ("test_session_1",))
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "Alice"

    def test_insert_game_turn_with_foreign_key(self):
        """Should be able to insert game_turn with session foreign key."""
        cursor = self.conn.cursor()

        # First insert session
        cursor.execute(
            "INSERT INTO sessions (id, player_name, status) VALUES (?, ?, ?)",
            ("test_session_2", "Bob", "active"),
        )

        # Then insert game_turn
        cursor.execute(
            """
            INSERT INTO game_turns (session_id, turn_number, state_snapshot)
            VALUES (?, ?, ?)
            """,
            ("test_session_2", 0, '{"test": "state"}'),
        )
        self.conn.commit()

        # Verify
        cursor.execute(
            "SELECT * FROM game_turns WHERE session_id = ?", ("test_session_2",)
        )
        row = cursor.fetchone()
        assert row is not None


class TestSchemaIndexes:
    """Test that performance indexes are created."""

    @pytest.fixture(autouse=True)
    def setup_db(self, schema_path, temp_db):
        """Create database with schema."""
        schema = load_schema(schema_path)
        self.conn = sqlite3.connect(temp_db)
        self.conn.executescript(schema)
        self.conn.commit()
        yield
        self.conn.close()

    def test_critical_indexes_exist(self):
        """Critical query indexes should exist."""
        cursor = self.conn.cursor()

        # List all indexes
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        # Verify critical indexes
        assert "idx_sessions_status" in indexes
        assert "idx_game_turns_session_turn" in indexes
        assert "idx_safe_function_calls_session_turn" in indexes


class TestSchemaIntegration:
    """Integration tests for the complete schema."""

    @pytest.fixture(autouse=True)
    def setup_db(self, schema_path, temp_db):
        """Create database with schema."""
        schema = load_schema(schema_path)
        self.conn = sqlite3.connect(temp_db)
        self.conn.executescript(schema)
        self.conn.commit()
        yield
        self.conn.close()

    def test_full_game_session_workflow(self):
        """Test complete game session workflow."""
        cursor = self.conn.cursor()

        # Create session
        cursor.execute(
            """
            INSERT INTO sessions (id, player_name, theme_id, status)
            VALUES (?, ?, ?, ?)
            """,
            ("workflow_session", "TestPlayer", "siege_default", "active"),
        )
        self.conn.commit()

        # Add game turn
        cursor.execute(
            """
            INSERT INTO game_turns (session_id, turn_number, state_snapshot, player_choice_id)
            VALUES (?, ?, ?, ?)
            """,
            ("workflow_session", 1, '{"npcs": {}}', "observe"),
        )
        self.conn.commit()

        # Add safe function call
        cursor.execute(
            """
            INSERT INTO safe_function_calls (session_id, turn_number, function_name, success)
            VALUES (?, ?, ?, ?)
            """,
            ("workflow_session", 1, "move_npc", True),
        )
        self.conn.commit()

        # Add checkpoint
        cursor.execute(
            """
            INSERT INTO checkpoints (session_id, turn_number, state, reason)
            VALUES (?, ?, ?, ?)
            """,
            ("workflow_session", 1, '{"backup": "data"}', "auto_backup"),
        )
        self.conn.commit()

        # Verify all data persisted
        cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE id = ?", ("workflow_session",)
        )
        assert cursor.fetchone()[0] == 1

        cursor.execute(
            "SELECT COUNT(*) FROM game_turns WHERE session_id = ?",
            ("workflow_session",),
        )
        assert cursor.fetchone()[0] == 1

        cursor.execute(
            "SELECT COUNT(*) FROM safe_function_calls WHERE session_id = ?",
            ("workflow_session",),
        )
        assert cursor.fetchone()[0] == 1

        cursor.execute(
            "SELECT COUNT(*) FROM checkpoints WHERE session_id = ?",
            ("workflow_session",),
        )
        assert cursor.fetchone()[0] == 1

    def test_cascade_delete_on_session_delete(self):
        """Deleting a session should cascade to related records."""
        cursor = self.conn.cursor()

        # Enable foreign keys for cascade delete to work
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create session and related data
        cursor.execute(
            "INSERT INTO sessions (id, player_name, status) VALUES (?, ?, ?)",
            ("cascade_session", "Tester", "active"),
        )
        cursor.execute(
            "INSERT INTO game_turns (session_id, turn_number, state_snapshot) VALUES (?, ?, ?)",
            ("cascade_session", 1, "{}"),
        )
        self.conn.commit()

        # Verify data exists
        cursor.execute(
            "SELECT COUNT(*) FROM game_turns WHERE session_id = ?", ("cascade_session",)
        )
        assert cursor.fetchone()[0] == 1

        # Delete session
        cursor.execute("DELETE FROM sessions WHERE id = ?", ("cascade_session",))
        self.conn.commit()

        # Verify cascade delete worked
        cursor.execute(
            "SELECT COUNT(*) FROM game_turns WHERE session_id = ?", ("cascade_session",)
        )
        assert (
            cursor.fetchone()[0] == 0
        ), "Cascade delete should have removed related game_turns"
