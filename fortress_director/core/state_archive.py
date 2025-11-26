"""State Archive System - Solves state bloat and LLM context window issues.

Implements 3-tier state management:
1. Current (5 recent turns) - full state
2. Recent History (5-10 turns) - state deltas
3. Archive (turns 1-90+) - summarized events

This allows:
- Constant memory usage (O(1) instead of O(n) with turns)
- LLM context preservation (insert relevant summary into prompts)
- Narrative continuity (LLM knows major events from past)
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger(__name__)

MAX_CURRENT_TURNS = 6  # Keep full state for recent 6 turns
MAX_RECENT_HISTORY = 10  # Keep deltas for 5-10 turns back
ARCHIVE_INTERVAL = 10  # Compress every 10 turns


class StateArchive:
    """Manages 3-tier state: current, recent history, archive."""

    def __init__(self, session_id: str):
        """Initialize archive for a session.

        Args:
            session_id: Session identifier for logging
        """
        self.session_id = session_id
        # turn -> full state
        self.current_states: Dict[int, Dict[str, Any]] = {}
        # turn -> delta
        self.recent_deltas: Dict[int, Dict[str, Any]] = {}
        # category -> summary text
        self.archive_summaries: Dict[str, str] = {}
        # Major events
        self.event_log: List[str] = []
        # npc_id -> status timeline
        self.npc_status_history: Dict[str, List[str]] = {}
        # Threat scores over time
        self.threat_timeline: List[float] = []

    def record_turn(
        self,
        turn_number: int,
        full_state: Dict[str, Any],
        state_delta: Dict[str, Any],
    ) -> None:
        """Record a turn's state and delta.

        Args:
            turn_number: Current turn
            full_state: Complete game state
            state_delta: Changes from previous state
        """
        # Keep current state for recent turns only
        if turn_number <= MAX_CURRENT_TURNS:
            self.current_states[turn_number] = full_state.copy()
        else:
            # For old turns, keep only delta
            self.recent_deltas[turn_number] = state_delta.copy()

        # Record threat trend
        threat = full_state.get("world", {}).get("threat_level")
        if threat:
            self.threat_timeline.append(threat)
            # Keep only recent history
            if len(self.threat_timeline) > MAX_RECENT_HISTORY * 2:
                self.threat_timeline = self.threat_timeline[-MAX_RECENT_HISTORY:]

        # Record NPC status changes
        self._track_npc_changes(full_state)

        # Extract major events
        self._extract_events(state_delta)

        # Compress to archive periodically
        if turn_number > 0 and turn_number % ARCHIVE_INTERVAL == 0:
            self._compress_to_archive(turn_number)

    def _track_npc_changes(self, state: Dict[str, Any]) -> None:
        """Track NPC status changes."""
        npcs = state.get("npc_locations", [])
        for npc in npcs:
            npc_id = npc.get("id")
            if not npc_id:
                continue
            if npc_id not in self.npc_status_history:
                self.npc_status_history[npc_id] = []

            # Summarize NPC status
            status = (
                f"Morale:{npc.get('morale', '?')} "
                f"Fatigue:{npc.get('fatigue', '?')} "
                f"Pos:({npc.get('x', '?')},{npc.get('y', '?')})"
            )
            self.npc_status_history[npc_id].append(status)

            # Keep only recent
            if len(self.npc_status_history[npc_id]) > MAX_RECENT_HISTORY:
                statuses = self.npc_status_history[npc_id]
                self.npc_status_history[npc_id] = statuses[-MAX_RECENT_HISTORY:]

    def _extract_events(self, state_delta: Dict[str, Any]) -> None:
        """Extract major events from state delta."""
        if not state_delta:
            return

        # Recent events
        recent = state_delta.get("recent_events", [])
        for event in recent:
            if isinstance(event, str) and len(event) > 5:
                self.event_log.append(event)

        # Flags added (player decisions)
        flags = state_delta.get("flags_added", [])
        for flag in flags:
            self.event_log.append(f"Flag set: {flag}")

        # Keep only recent events
        if len(self.event_log) > MAX_RECENT_HISTORY * 3:
            self.event_log = self.event_log[-(MAX_RECENT_HISTORY * 3) :]

    def _compress_to_archive(self, turn_number: int) -> None:
        """Compress turns into archive summary.

        Args:
            turn_number: Current turn (checkpoint for archiving)
        """
        if turn_number < ARCHIVE_INTERVAL:
            return

        # Create archive summary
        archive_key = f"archive_{turn_number}"
        summary = self._build_archive_summary(turn_number)
        self.archive_summaries[archive_key] = summary

        LOGGER.debug(
            "[%s] Archived turns up to %d: %d bytes",
            self.session_id,
            turn_number,
            len(summary),
        )

    def _build_archive_summary(self, turn_number: int) -> str:
        """Build summary of events for archiving.

        Args:
            turn_number: Checkpoint turn

        Returns:
            Text summary of major events
        """
        summary_parts = []

        # Major events
        if self.event_log:
            summary_parts.append("=== MAJOR EVENTS ===")
            # Show only major events (long ones, flags)
            major = [e for e in self.event_log if len(e) > 20 or "Flag set:" in e][-10:]
            for event in major:
                summary_parts.append(f"• {event}")

        # NPC status summary
        if self.npc_status_history:
            summary_parts.append("\n=== NPC STATUS ===")
            for npc_id, statuses in self.npc_status_history.items():
                if statuses:
                    latest = statuses[-1]
                    summary_parts.append(f"• {npc_id}: {latest}")

        # Threat trend
        if self.threat_timeline:
            trend = (
                "rising"
                if self.threat_timeline[-1] > self.threat_timeline[0]
                else "stable/falling"
            )
            summary_parts.append(
                f"\n=== THREAT TREND ===\n"
                f"• Started: {self.threat_timeline[0]:.1f}\n"
                f"• Now: {self.threat_timeline[-1]:.1f}\n"
                f"• Trend: {trend}"
            )

        return "\n".join(summary_parts)

    def get_context_for_prompt(self, turn_number: int) -> Optional[str]:
        """Get archive context to inject into LLM prompt.

        Args:
            turn_number: Current turn

        Returns:
            Summary text to include in prompt, or None
        """
        # Inject archive starting at ARCHIVE_INTERVAL, every 8-10 turns
        if turn_number < ARCHIVE_INTERVAL:
            return None

        # Check if we should inject at this turn (every ~8 turns)
        last_injection = (turn_number - ARCHIVE_INTERVAL) // 8
        current_injection = turn_number // 8
        if last_injection == current_injection:
            return None  # Wait for next injection window

        # Find most recent archive
        archive_keys = sorted(self.archive_summaries.keys())
        if not archive_keys:
            return None

        latest_key = archive_keys[-1]
        return self.archive_summaries[latest_key]

    def get_current_state_size(self) -> int:
        """Estimate current memory usage."""
        size = 0
        size += sum(len(json.dumps(s)) for s in self.current_states.values())
        size += sum(len(json.dumps(d)) for d in self.recent_deltas.values())
        size += sum(len(s) for s in self.archive_summaries.values())
        size += sum(len(e) for e in self.event_log)
        return size

    def compact(self, max_size_bytes: int = 1_000_000) -> None:
        """Compact archive if it exceeds max size.

        Args:
            max_size_bytes: Maximum allowed size (default 1MB)
        """
        current_size = self.get_current_state_size()
        if current_size > max_size_bytes:
            # Aggressive cleanup
            self.event_log = self.event_log[-50:]  # Keep only last 50
            self.recent_deltas.clear()  # Remove old deltas
            LOGGER.warning(
                "[%s] Archive compacted to %d bytes",
                self.session_id,
                self.get_current_state_size(),
            )

    def to_dict(self) -> Dict[str, Any]:
        """Export archive to dict (for serialization)."""
        return {
            "current_states": {k: v for k, v in self.current_states.items()},
            "recent_deltas": {k: v for k, v in self.recent_deltas.items()},
            "archive_summaries": self.archive_summaries.copy(),
            "event_log": self.event_log[-100:],  # Keep recent
            "npc_status_history": self.npc_status_history.copy(),
            "threat_timeline": self.threat_timeline[-100:],
        }

    @classmethod
    def from_dict(cls, session_id: str, data: Dict[str, Any]) -> "StateArchive":
        """Restore archive from dict."""
        archive = cls(session_id)
        archive.current_states = data.get("current_states", {})
        archive.recent_deltas = data.get("recent_deltas", {})
        archive.archive_summaries = data.get("archive_summaries", {})
        archive.event_log = data.get("event_log", [])
        archive.npc_status_history = data.get("npc_status_history", {})
        archive.threat_timeline = data.get("threat_timeline", [])
        return archive

    def save_to_db(self, db_path: str, turn_number: int) -> bool:
        """Save archive to SQLite database.

        Args:
            db_path: Path to database file
            turn_number: Current turn (for progress tracking)

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Create archive tables if needed
            archive_schema_path = Path(__file__).parent.parent / "db"
            archive_schema_path = archive_schema_path / "archive_schema.sql"
            if archive_schema_path.exists():
                with open(archive_schema_path, "r") as f:
                    cursor.executescript(f.read())

            # Save metadata
            cursor.execute(
                """
                INSERT OR REPLACE INTO archive_metadata
                    (session_id, last_saved_turn, last_saved_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (self.session_id, turn_number),
            )

            # Save current states
            for turn, state in self.current_states.items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO archive_turns
                        (session_id, turn_number, tier, snapshot_type, data)
                    VALUES (?, ?, 'current', 'full', ?)
                    """,
                    (
                        self.session_id,
                        turn,
                        json.dumps(state),
                    ),
                )

            # Save recent deltas
            for turn, delta in self.recent_deltas.items():
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO archive_turns
                        (session_id, turn_number, tier, snapshot_type, data)
                    VALUES (?, ?, 'recent', 'delta', ?)
                    """,
                    (
                        self.session_id,
                        turn,
                        json.dumps(delta),
                    ),
                )

            # Save threat timeline
            for turn, threat in enumerate(self.threat_timeline, 1):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO archive_threats
                        (session_id, turn_number, threat_score)
                    VALUES (?, ?, ?)
                    """,
                    (
                        self.session_id,
                        turn,
                        threat,
                    ),
                )

            # Save NPC status history
            for npc_id, statuses in self.npc_status_history.items():
                for turn, status in enumerate(statuses, 1):
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO archive_npcs
                        (session_id, turn_number, npc_id, status)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            self.session_id,
                            turn,
                            npc_id,
                            status,
                        ),
                    )

            conn.commit()
            conn.close()
            LOGGER.info(
                "[%s] Archive saved to DB (turn %d)",
                self.session_id,
                turn_number,
            )
            return True

        except Exception as e:
            LOGGER.error(
                "[%s] Failed to save archive to DB: %s",
                self.session_id,
                e,
            )
            return False

    @classmethod
    def load_from_db(cls, db_path: str, session_id: str) -> Optional["StateArchive"]:
        """Load archive from SQLite database.

        Args:
            db_path: Path to database file
            session_id: Session identifier

        Returns:
            StateArchive instance or None if not found
        """
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            archive = cls(session_id)

            # Load current states
            cursor.execute(
                """
                SELECT turn_number, data FROM archive_turns
                WHERE session_id = ? AND tier = 'current'
                ORDER BY turn_number
                """,
                (session_id,),
            )
            for row in cursor.fetchall():
                turn = row["turn_number"]
                data = json.loads(row["data"])
                archive.current_states[turn] = data

            # Load recent deltas
            cursor.execute(
                """
                SELECT turn_number, data FROM archive_turns
                WHERE session_id = ? AND tier = 'recent'
                ORDER BY turn_number
                """,
                (session_id,),
            )
            for row in cursor.fetchall():
                turn = row["turn_number"]
                data = json.loads(row["data"])
                archive.recent_deltas[turn] = data

            # Load threat timeline
            cursor.execute(
                """
                SELECT threat_score FROM archive_threats
                WHERE session_id = ?
                ORDER BY turn_number
                """,
                (session_id,),
            )
            archive.threat_timeline = [
                row["threat_score"]
                for row in cursor.fetchall()
                if row["threat_score"] is not None
            ]

            # Load NPC status
            cursor.execute(
                """
                SELECT npc_id, status, turn_number
                FROM archive_npcs
                WHERE session_id = ?
                ORDER BY turn_number
                """,
                (session_id,),
            )
            for row in cursor.fetchall():
                npc_id = row["npc_id"]
                if npc_id not in archive.npc_status_history:
                    archive.npc_status_history[npc_id] = []
                archive.npc_status_history[npc_id].append(row["status"])

            conn.close()
            LOGGER.info(
                "[%s] Archive loaded from DB",
                session_id,
            )
            return archive

        except Exception as e:
            LOGGER.error(
                "[%s] Failed to load archive from DB: %s",
                session_id,
                e,
            )
            return None


def inject_archive_to_prompt(
    archive: StateArchive, current_turn: int, prompt: str
) -> str:
    """Inject archive context into LLM prompt.

    Args:
        archive: StateArchive instance
        current_turn: Current turn number
        prompt: Original prompt

    Returns:
        Prompt with archive context injected
    """
    context = archive.get_context_for_prompt(current_turn)
    if not context:
        return prompt

    # Inject at beginning (after system prompt, before current state)
    archive_start = current_turn - ARCHIVE_INTERVAL
    injected = f"""{prompt}

--- HISTORICAL CONTEXT (turns 1-{archive_start}) ---
{context}

--- CURRENT SITUATION (turn {current_turn}) ---
"""
    return injected
