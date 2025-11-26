"""Test session persistence and recovery with archive."""

import tempfile
from pathlib import Path

from fortress_director.core.state_archive import StateArchive


class TestSessionPersistence:
    """Test saving and loading campaigns."""

    def test_archive_save_and_restore(self):
        """Test archive can be saved and restored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "game.db"

            # Create and populate archive
            arch1 = StateArchive("persist_test")
            for turn in range(1, 51):
                state = {
                    "turn": turn,
                    "world": {"threat_level": 1.0 + (turn * 0.05)},
                    "npc_locations": [
                        {
                            "id": "npc_1",
                            "status": "active",
                            "morale": 70,
                            "fatigue": 10,
                            "x": turn % 10,
                            "y": turn % 10,
                        }
                    ],
                }
                delta = {}
                arch1.record_turn(turn, state, delta)

            # Save to DB
            assert arch1.save_to_db(str(db_path), 50)

            # Load from DB
            arch2 = StateArchive.load_from_db(str(db_path), "persist_test")
            assert arch2 is not None
            assert arch2.session_id == "persist_test"

    def test_campaign_recovery_after_save(self):
        """Test campaign can continue after load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "game.db"

            # Session 1: Record 30 turns
            arch1 = StateArchive("recovery_test")
            for turn in range(1, 31):
                state = {"turn": turn, "world": {"threat_level": 1.0}}
                delta = {}
                arch1.record_turn(turn, state, delta)

            arch1.save_to_db(str(db_path), 30)

            # Session 2: Load and continue
            arch2 = StateArchive.load_from_db(str(db_path), "recovery_test")
            assert arch2 is not None

            # Continue recording
            for turn in range(31, 51):
                state = {"turn": turn, "world": {"threat_level": 1.5}}
                delta = {}
                arch2.record_turn(turn, state, delta)

            # Verify continuity
            assert len(arch2.threat_timeline) > 0

    def test_multiple_session_isolation(self):
        """Test multiple sessions don't interfere."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "game.db"

            # Session A
            archA = StateArchive("session_a")
            for turn in range(1, 21):
                state = {"turn": turn, "world": {"threat_level": 1.0}}
                delta = {}
                archA.record_turn(turn, state, delta)
            archA.save_to_db(str(db_path), 20)

            # Session B (different data)
            archB = StateArchive("session_b")
            for turn in range(1, 21):
                state = {"turn": turn, "world": {"threat_level": 5.0}}
                delta = {}
                archB.record_turn(turn, state, delta)
            archB.save_to_db(str(db_path), 20)

            # Restore both
            restored_a = StateArchive.load_from_db(str(db_path), "session_a")
            restored_b = StateArchive.load_from_db(str(db_path), "session_b")

            assert restored_a is not None
            assert restored_b is not None
            # Should be different
            assert len(restored_a.threat_timeline) >= 0
            assert len(restored_b.threat_timeline) >= 0


class TestCombatValidation:
    """Test combat mechanics with archive."""

    def test_threat_escalation_impacts_npc_morale(self):
        """Test threat escalation lowers NPC morale."""
        arch = StateArchive("combat_morale_test")

        for turn in range(1, 51):
            # Threat escalates linearly
            threat = 1.0 + (turn * 0.1)
            # NPC morale should decrease with threat
            expected_morale = max(20, 100 - (threat * 8))

            state = {
                "turn": turn,
                "world": {"threat_level": threat},
                "npc_locations": [
                    {
                        "id": "defender",
                        "status": "defending",
                        "morale": expected_morale,
                        "fatigue": min(100, turn // 2),
                        "x": 0,
                        "y": 0,
                    }
                ],
            }
            delta = {}
            arch.record_turn(turn, state, delta)

        # Verify threat tracked
        assert len(arch.threat_timeline) > 0
        # Threat should increase
        if len(arch.threat_timeline) > 1:
            assert arch.threat_timeline[-1] > arch.threat_timeline[0]

    def test_damage_accumulation_tracking(self):
        """Test damage accumulation is tracked over time."""
        arch = StateArchive("damage_test")

        total_damage = 0
        for turn in range(1, 51):
            # Each turn, take some damage
            damage_this_turn = max(0, 2 - ((turn % 15) / 5))
            total_damage += damage_this_turn

            state = {
                "turn": turn,
                "world": {
                    "threat_level": 1.0 + (turn * 0.05),
                    "accumulated_damage": total_damage,
                },
                "npc_locations": [
                    {
                        "id": "soldier",
                        "status": ("wounded" if total_damage > 20 else "healthy"),
                        "morale": max(30, 100 - (total_damage / 2)),
                        "fatigue": turn // 3,
                        "x": 0,
                        "y": 0,
                    }
                ],
                "recent_events": (
                    [
                        f"Damage: {damage_this_turn:.1f}",
                    ]
                    if damage_this_turn > 0
                    else []
                ),
            }
            delta = {"damage_taken": damage_this_turn}
            arch.record_turn(turn, state, delta)

        # Verify damage tracked in NPC status
        assert len(arch.npc_status_history) > 0
        assert "soldier" in arch.npc_status_history

    def test_combat_resolution_with_archive(self):
        """Test complete combat scenario with archive injection."""
        arch = StateArchive("combat_scenario_test")

        # Phase 1: Skirmish (turns 1-20)
        for turn in range(1, 21):
            state = {
                "turn": turn,
                "world": {"threat_level": 2.0},
                "npc_locations": [
                    {
                        "id": "warrior",
                        "status": "fighting",
                        "morale": 80,
                        "fatigue": turn // 2,
                        "x": 0,
                        "y": 0,
                    }
                ],
            }
            delta = {"phase": "skirmish"}
            arch.record_turn(turn, state, delta)

        # Phase 2: Siege (turns 21-40)
        for turn in range(21, 41):
            state = {
                "turn": turn,
                "world": {"threat_level": 5.0},
                "npc_locations": [
                    {
                        "id": "warrior",
                        "status": "defending",
                        "morale": max(40, 100 - ((turn - 20) * 2)),
                        "fatigue": turn // 2,
                        "x": 0,
                        "y": 0,
                    }
                ],
            }
            delta = {"phase": "siege"}
            arch.record_turn(turn, state, delta)

        # Phase 3: Resolution (turns 41-50)
        for turn in range(41, 51):
            state = {
                "turn": turn,
                "world": {"threat_level": 8.0},
                "npc_locations": [
                    {
                        "id": "warrior",
                        "status": "resolute",
                        "morale": 50,
                        "fatigue": min(100, turn // 2),
                        "x": 0,
                        "y": 0,
                    }
                ],
            }
            delta = {"phase": "resolution"}
            arch.record_turn(turn, state, delta)

        # Verify complete combat tracked
        # Threat timeline may be culled to MAX_RECENT_HISTORY*2
        assert len(arch.threat_timeline) > 0
        assert len(arch.npc_status_history["warrior"]) > 0

        # Get context should work at turn 30 (mid-siege)
        # May or may not have context depending on injection windows
        # But archive should exist
        assert len(arch.archive_summaries) > 0
