from fastapi.testclient import TestClient
import sqlite3
import tempfile
from pathlib import Path

from fortress_director import api
from fortress_director.llm.runtime_mode import set_llm_enabled
from fortress_director.db.session_store import SessionStore

set_llm_enabled(False)


# Initialize test database with sessions table
def _init_test_db():
    """Create test database with required tables."""
    # Create temp db if it doesn't exist
    db_path = Path(tempfile.gettempdir()) / "test_fortress.db"
    if not db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                theme_id TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

    # Patch session store to use test database
    import fortress_director.db.session_store as ss

    ss._session_store = SessionStore(db_path=str(db_path))


_init_test_db()


def test_list_themes_endpoint_returns_builtin_catalog() -> None:
    client = TestClient(api.app)
    response = client.get("/api/themes")
    assert response.status_code == 200
    payload = response.json()
    assert "themes" in payload
    ids = {entry["id"] for entry in payload["themes"]}
    assert {"siege_default", "orbital_outpost"}.issubset(ids)


def test_run_turn_with_theme_id_and_session_consistency() -> None:
    client = TestClient(api.app)
    first = client.post(
        "/api/run_turn",
        json={"choice_id": "alpha", "theme_id": "orbital_outpost"},
    )
    assert first.status_code == 200
    first_payload = first.json()
    session_id = first_payload["session_id"]
    assert first_payload["theme_id"] == "orbital_outpost"
    assert first_payload["event_node_id"] == "uplink_init"

    follow_up = client.post(
        "/api/run_turn",
        json={"session_id": session_id, "theme_id": "orbital_outpost"},
    )
    assert follow_up.status_code == 200

    mismatch = client.post(
        "/api/run_turn",
        json={"session_id": session_id, "theme_id": "siege_default"},
    )
    assert mismatch.status_code == 400


def test_reset_for_new_run_accepts_theme_id() -> None:
    client = TestClient(api.app)
    response = client.post(
        "/api/reset_for_new_run",
        json={"theme_id": "orbital_outpost"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["theme_id"] == "orbital_outpost"
