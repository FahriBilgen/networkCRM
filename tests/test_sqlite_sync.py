from __future__ import annotations

import sqlite3
from pathlib import Path

from fortress_director.utils.sqlite_sync import SQLiteStateSync


def _sample_state() -> dict:
    return {
        "schema_version": 2,
        "turn": 3,
        "day": 1,
        "time": "noon",
        "npc_locations": {"rhea": "western_wall"},
        "npc_trust": {"rhea": 4},
        "npc_schedule": {
            "rhea": [
                {
                    "activity": "patrol",
                    "duration": 2,
                    "assigned_turn": 3,
                }
            ]
        },
        "structures": {
            "western_wall": {
                "durability": 80,
                "max_durability": 100,
                "status": "stable",
            }
        },
        "stockpiles": {"food": 120},
        "trade_routes": {
            "northern_pass": {
                "status": "open",
                "risk": 1,
                "reward": 4,
                "opened_turn": 2,
            }
        },
        "scheduled_events": [
            {
                "event_id": "wall_collapse",
                "trigger_turn": 5,
            }
        ],
        "timeline": [
            {
                "turn": 3,
                "type": "time_shift",
                "from": "dawn",
                "to": "noon",
            }
        ],
        "environment_hazards": [
            {
                "hazard_id": "rockslide",
                "severity": 3,
                "remaining": 2,
                "origin_turn": 2,
            }
        ],
        "combat_log": [
            {
                "turn": 3,
                "attacker": "rhea",
                "defender": "raider",
                "outcome": "attacker_win",
            }
        ],
        "story_progress": {
            "act": "build_up",
            "progress": 0.4,
            "act_history": [
                {
                    "act": "build_up",
                    "progress": 0.4,
                    "turn": 3,
                }
            ],
        },
    }


def test_sqlite_sync_persists_core_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "game_state.sqlite"
    syncer = SQLiteStateSync(db_path=db_path)
    syncer.sync(_sample_state())

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        turn_row = cursor.execute(
            "SELECT value FROM metadata WHERE key = 'turn'",
        ).fetchone()
        assert turn_row[0] == "3"

        npc_row = cursor.execute(
            "SELECT location, trust FROM npc_state WHERE npc_id = ?",
            ("rhea",),
        ).fetchone()
        assert npc_row == ("western_wall", 4)

        structure_row = cursor.execute(
            "SELECT durability FROM structure_state WHERE structure_id = ?",
            ("western_wall",),
        ).fetchone()
        assert structure_row[0] == 80

        trade_row = cursor.execute(
            "SELECT status FROM trade_routes WHERE route_id = ?",
            ("northern_pass",),
        ).fetchone()
        assert trade_row[0] == "open"

        hazard_row = cursor.execute(
            "SELECT severity FROM hazard_log WHERE hazard_id = ?",
            ("rockslide",),
        ).fetchone()
        assert hazard_row[0] == 3

        story_row = cursor.execute(
            "SELECT progress FROM story_progress WHERE act = ?",
            ("build_up",),
        ).fetchone()
        assert story_row[0] == 0.4
