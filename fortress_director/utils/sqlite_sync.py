"""SQLite mirror synchronisation for Fortress Director world state."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from fortress_director.settings import SETTINGS

LOGGER = logging.getLogger(__name__)


class SQLiteStateSync:
    """Synchronise the JSON world state into the SQLite mirror."""

    def __init__(
        self,
        *,
        db_path: Path | None = None,
        schema_path: Path | None = None,
    ) -> None:
        self._db_path = Path(db_path or SETTINGS.db_path)
        if schema_path is not None:
            self._schema_path = Path(schema_path)
        else:
            candidates = [
                SETTINGS.project_root / "db" / "schema.sql",
                SETTINGS.project_root.parent / "db" / "schema.sql",
            ]
            for candidate in candidates:
                if candidate.exists() and candidate.stat().st_size > 0:
                    self._schema_path = candidate
                    break
            else:
                self._schema_path = candidates[0]

    def sync(
        self,
        state: Dict[str, Any],
        *,
        changed_keys: Optional[Set[str]] = None,
    ) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            self._ensure_schema(conn)
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            try:
                self._sync_metadata(cursor, state)
                if self._should_sync(changed_keys, {"npc_trust", "npc_schedule", "npc_locations", "npc_fragments"}):
                    self._sync_npc_state(cursor, state)
                if self._should_sync(changed_keys, {"structures"}):
                    self._sync_structure_state(cursor, state)
                if self._should_sync(changed_keys, {"stockpiles", "stockpile_log"}):
                    self._sync_stockpiles(cursor, state)
                if self._should_sync(changed_keys, {"trade_routes", "trade_route_history"}):
                    self._sync_trade_routes(cursor, state)
                if self._should_sync(changed_keys, {"scheduled_events"}):
                    self._sync_scheduled_events(cursor, state)
                if self._should_sync(changed_keys, {"timeline"}):
                    self._sync_timeline(cursor, state)
                if self._should_sync(changed_keys, {"environment_hazards", "weather_pattern", "hazard_cooldowns"}):
                    self._sync_hazards(cursor, state)
                if self._should_sync(changed_keys, {"combat_log"}):
                    self._sync_combat_log(cursor, state)
                if self._should_sync(changed_keys, {"story_progress"}):
                    self._sync_story_progress(cursor, state)
            except Exception as exc:
                conn.rollback()
                LOGGER.exception("SQLite sync failed: %s", exc)
                raise
            else:
                conn.commit()

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        # Be defensive: try to apply the full schema SQL file. If it is
        # missing or cannot be applied for any reason, fall back to
        # creating the minimal core tables that other code expects so
        # tests running against a fresh DB do not fail with
        # "no such table" errors.
        try:
            if self._schema_path.exists() and self._schema_path.stat().st_size > 0:
                schema_sql = self._schema_path.read_text(encoding="utf-8")
                if schema_sql.strip():
                    conn.executescript(schema_sql)
                    return
        except Exception:
            LOGGER.warning(
                "Failed to read/execute schema from %s; falling back to core"
                " table creation",
                self._schema_path,
            )

        # Minimal fallback schema: create only the highest-value tables
        # required by the sync routines. Use IF NOT EXISTS to be idempotent.
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS npc_state (
                npc_id TEXT PRIMARY KEY,
                name TEXT,
                template TEXT,
                location TEXT,
                status TEXT,
                trust INTEGER DEFAULT 0,
                last_updated_turn INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS structure_state (
                structure_id TEXT PRIMARY KEY,
                durability INTEGER NOT NULL,
                max_durability INTEGER NOT NULL,
                status TEXT,
                last_repaired_turn INTEGER,
                last_reinforced_turn INTEGER
            );
            CREATE TABLE IF NOT EXISTS stockpiles (
                resource_id TEXT PRIMARY KEY,
                quantity INTEGER NOT NULL,
                last_updated_turn INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS timeline_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )

    def _sync_metadata(
        self,
        cursor: sqlite3.Cursor,
        state: Dict[str, Any],
    ) -> None:
        entries = {
            "schema_version": state.get("schema_version"),
            "turn": state.get("turn"),
            "day": state.get("day"),
            "time": state.get("time"),
        }
        cursor.execute("DELETE FROM metadata")
        rows = [
            (key, str(value)) for key, value in entries.items() if value is not None
        ]
        if rows:
            cursor.executemany(
                "INSERT INTO metadata (key, value) VALUES (?, ?)",
                rows,
            )

    def _sync_npc_state(
        self,
        cursor: sqlite3.Cursor,
        state: Dict[str, Any],
    ) -> None:
        locations = state.get("npc_locations", {})
        trust_map = state.get("npc_trust", {})
        schedules = state.get("npc_schedule", {})
        actors = set(locations) | set(trust_map) | set(schedules)
        rows: List[Tuple[Any, ...]] = []
        for npc_id in sorted(actors):
            location = locations.get(npc_id)
            trust = _safe_int(trust_map.get(npc_id))
            queue = schedules.get(npc_id) or []
            last_turn = _last_assigned_turn(queue, state)
            status = "active" if location or queue else None
            rows.append(
                (
                    npc_id,
                    None,
                    None,
                    location,
                    status,
                    trust,
                    last_turn,
                )
            )
        _replace_table(
            cursor,
            "npc_state",
            (
                "npc_id",
                "name",
                "template",
                "location",
                "status",
                "trust",
                "last_updated_turn",
            ),
            rows,
        )

    def _sync_structure_state(
        self,
        cursor: sqlite3.Cursor,
        state: Dict[str, Any],
    ) -> None:
        structures = state.get("structures", {})
        rows = []
        for struct_id, payload in sorted(structures.items()):
            rows.append(
                (
                    struct_id,
                    _safe_int(payload.get("durability")),
                    _safe_int(payload.get("max_durability"), default=100),
                    payload.get("status"),
                    _safe_int(
                        payload.get("last_repaired_turn"),
                        allow_none=True,
                    ),
                    _safe_int(
                        payload.get("last_reinforced_turn"),
                        allow_none=True,
                    ),
                )
            )
        _replace_table(
            cursor,
            "structure_state",
            (
                "structure_id",
                "durability",
                "max_durability",
                "status",
                "last_repaired_turn",
                "last_reinforced_turn",
            ),
            rows,
        )

    def _sync_stockpiles(
        self,
        cursor: sqlite3.Cursor,
        state: Dict[str, Any],
    ) -> None:
        stockpiles = state.get("stockpiles", {})
        rows = [
            (resource_id, _safe_int(quantity), _safe_int(state.get("turn")))
            for resource_id, quantity in sorted(stockpiles.items())
        ]
        _replace_table(
            cursor,
            "stockpiles",
            ("resource_id", "quantity", "last_updated_turn"),
            rows,
        )

    def _sync_trade_routes(
        self,
        cursor: sqlite3.Cursor,
        state: Dict[str, Any],
    ) -> None:
        routes = state.get("trade_routes", {})
        rows = []
        for route_id, payload in sorted(routes.items()):
            rows.append(
                (
                    route_id,
                    payload.get("status", "unknown"),
                    _safe_int(payload.get("risk")),
                    _safe_int(payload.get("reward")),
                    _safe_int(payload.get("opened_turn"), allow_none=True),
                    _safe_int(payload.get("closed_turn"), allow_none=True),
                    payload.get("reason"),
                )
            )
        _replace_table(
            cursor,
            "trade_routes",
            (
                "route_id",
                "status",
                "risk",
                "reward",
                "opened_turn",
                "closed_turn",
                "last_reason",
            ),
            rows,
        )

    def _sync_scheduled_events(
        self,
        cursor: sqlite3.Cursor,
        state: Dict[str, Any],
    ) -> None:
        scheduled = state.get("scheduled_events", [])
        rows = []
        for entry in scheduled:
            event_id = entry.get("event_id")
            if not event_id:
                continue
            rows.append(
                (
                    event_id,
                    _safe_int(entry.get("trigger_turn")),
                    entry.get("status", "scheduled"),
                )
            )
        _replace_table(
            cursor,
            "scheduled_events",
            ("event_id", "trigger_turn", "status"),
            rows,
        )

    def _sync_timeline(
        self,
        cursor: sqlite3.Cursor,
        state: Dict[str, Any],
    ) -> None:
        timeline = state.get("timeline", [])
        rows = []
        for entry in timeline:
            turn = _safe_int(
                entry.get("turn"),
                default=_safe_int(state.get("turn")),
            )
            event_type = entry.get("type", "unknown")
            payload_json = json.dumps(entry, sort_keys=True)
            rows.append((turn, event_type, payload_json))
        _replace_table(
            cursor,
            "timeline_events",
            ("turn", "event_type", "payload_json"),
            rows,
        )

    def _sync_hazards(
        self,
        cursor: sqlite3.Cursor,
        state: Dict[str, Any],
    ) -> None:
        hazards = state.get("environment_hazards", [])
        rows = []
        default_turn = _safe_int(state.get("turn"))
        for entry in hazards:
            hazard_id = entry.get("hazard_id")
            if not hazard_id:
                continue
            turn = _safe_int(
                entry.get("last_triggered") or entry.get("origin_turn"),
                default=default_turn,
            )
            rows.append(
                (
                    hazard_id,
                    turn,
                    _safe_int(entry.get("severity")),
                    _safe_int(entry.get("remaining"), default=0),
                )
            )
        _replace_table(
            cursor,
            "hazard_log",
            ("hazard_id", "turn", "severity", "duration"),
            rows,
        )

    def _sync_combat_log(
        self,
        cursor: sqlite3.Cursor,
        state: Dict[str, Any],
    ) -> None:
        combat_log = state.get("combat_log", [])
        rows = []
        for entry in combat_log:
            rows.append(
                (
                    _safe_int(
                        entry.get("turn"),
                        default=_safe_int(state.get("turn")),
                    ),
                    entry.get("attacker"),
                    entry.get("defender"),
                    entry.get("outcome"),
                )
            )
        _replace_table(
            cursor,
            "combat_log",
            ("turn", "attacker", "defender", "outcome"),
            rows,
        )

    def _sync_story_progress(
        self,
        cursor: sqlite3.Cursor,
        state: Dict[str, Any],
    ) -> None:
        story = state.get("story_progress", {})
        history = story.get("act_history", []) or []
        rows = []
        for entry in history:
            act = entry.get("act")
            if not act:
                continue
            rows.append(
                (
                    act,
                    _safe_float(entry.get("progress"), default=0.0),
                    _safe_int(
                        entry.get("turn"),
                        default=_safe_int(state.get("turn")),
                    ),
                )
            )
        if not rows and story.get("act"):
            rows.append(
                (
                    story.get("act"),
                    _safe_float(story.get("progress"), default=0.0),
                    _safe_int(state.get("turn")),
                )
            )
        _replace_table(
            cursor,
            "story_progress",
            ("act", "progress", "last_updated_turn"),
            rows,
        )

    @staticmethod
    def _should_sync(
        changed_keys: Optional[Set[str]],
        watched: Set[str],
    ) -> bool:
        if not changed_keys or not watched:
            return True
        return bool(changed_keys & watched)


def _replace_table(
    cursor: sqlite3.Cursor,
    table: str,
    columns: Sequence[str],
    rows: Iterable[Tuple[Any, ...]],
) -> None:
    cursor.execute(f"DELETE FROM {table}")
    rows_list = list(rows)
    if not rows_list:
        return
    placeholders = ",".join(["?"] * len(columns))
    column_list = ",".join(columns)
    cursor.executemany(
        f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})",
        rows_list,
    )


def _safe_int(
    value: Any,
    *,
    default: int = 0,
    allow_none: bool = False,
) -> int | None:
    if value is None:
        return None if allow_none else default
    try:
        return int(value)
    except (TypeError, ValueError):
        return None if allow_none else default


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _last_assigned_turn(
    queue: Sequence[Dict[str, Any]],
    state: Dict[str, Any],
) -> int:
    if not queue:
        return _safe_int(state.get("turn"))
    last = queue[-1]
    return _safe_int(
        last.get("assigned_turn"),
        default=_safe_int(state.get("turn")),
    )


_sync_cache: Dict[Path, SQLiteStateSync] = {}


def sync_state_to_sqlite(
    state: Dict[str, Any],
    *,
    db_path: Path | None = None,
    changed_keys: Optional[Set[str]] = None,
) -> None:
    path = Path(db_path or SETTINGS.db_path)
    syncer = _sync_cache.get(path)
    if syncer is None:
        syncer = SQLiteStateSync(db_path=path)
        _sync_cache[path] = syncer
    syncer.sync(state, changed_keys=changed_keys)
