"""Session persistence layer using SQLite."""

import sqlite3
from datetime import datetime
from typing import Optional

from fortress_director.settings import SETTINGS


class SessionStore:
    """Handle session persistence to database."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize session store with database path.

        Args:
            db_path: Path to SQLite database. Uses SETTINGS if not provided.
        """
        self.db_path = db_path or str(SETTINGS.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def record_session(
        self,
        session_id: str,
        theme_id: str,
    ) -> None:
        """Record a new session in the database.

        Args:
            session_id: Unique session identifier
            theme_id: Theme used for this session
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            created_at = datetime.utcnow().isoformat()

            cursor.execute(
                """
                INSERT INTO sessions (
                    session_id,
                    created_at,
                    theme_id
                ) VALUES (?, ?, ?)
                """,
                (session_id, created_at, theme_id),
            )

            conn.commit()
        except sqlite3.IntegrityError:
            # Session already exists (duplicate login attempt)
            pass
        finally:
            conn.close()

    def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session metadata from database.

        Args:
            session_id: Unique session identifier

        Returns:
            Session metadata dict or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT session_id, created_at, theme_id
                FROM sessions WHERE session_id = ?
                """,
                (session_id,),
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def list_sessions(self, limit: int = 100) -> list:
        """List recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session metadata dicts
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT session_id, created_at, theme_id
                FROM sessions
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def delete_session(self, session_id: str) -> None:
        """Delete a session from the database.

        Args:
            session_id: Unique session identifier
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,),
            )

            conn.commit()
        finally:
            conn.close()


# Global session store instance
_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """Get or create global session store instance."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
