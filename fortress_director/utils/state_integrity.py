"""State persistence verification and integrity checks."""

import logging
from pathlib import Path
from typing import Any, Dict
import json
import sqlite3

LOGGER = logging.getLogger(__name__)


def verify_state_integrity(
    json_path: Path,
    db_path: Path,
) -> Dict[str, Any]:
    """
    Verify that JSON and SQLite states are in sync.

    Returns dict with:
    - json_exists: bool
    - db_exists: bool
    - json_turn: int
    - db_turn: int
    - in_sync: bool
    """
    result = {
        "json_exists": False,
        "db_exists": False,
        "json_turn": None,
        "db_turn": None,
        "in_sync": False,
        "warnings": [],
    }

    # Check JSON
    if json_path.exists():
        try:
            json_data = json.loads(json_path.read_text(encoding="utf-8"))
            result["json_exists"] = True
            result["json_turn"] = json_data.get("turn")
        except Exception as e:
            result["warnings"].append(f"JSON read error: {e}")

    # Check SQLite
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM metadata WHERE key = ?", ("turn",))
                row = cursor.fetchone()
                if row:
                    result["db_exists"] = True
                    result["db_turn"] = int(row[0])
        except Exception as e:
            result["warnings"].append(f"SQLite read error: {e}")

    # Check sync
    if (
        result["json_exists"]
        and result["db_exists"]
        and result["json_turn"] == result["db_turn"]
    ):
        result["in_sync"] = True
    elif result["json_exists"] and result["db_exists"]:
        msg = f"Turn mismatch: JSON={result['json_turn']}, " f"DB={result['db_turn']}"
        result["warnings"].append(msg)

    return result
