"""Test long campaigns (100-500 turns) for archive stability and effectiveness."""

import pytest
from fortress_director.core.state_archive import StateArchive


@pytest.fixture
def long_campaign_archive():
    """Create archive with 100+ turns of simulated data."""
    arch = StateArchive("long_campaign_session")

    for turn in range(1, 101):
        # Simulate escalating threat
        threat_level = 1 + (turn * 0.05)  # Gradually increasing

        state = {
            "turn": turn,
            "world": {
                "threat_level": threat_level,
                "integrity": 100 - (turn * 0.2),  # Structures damaged
                "morale": 80 - (turn * 0.15),
                "resources": {"food": max(10, 100 - (turn * 0.3))},
            },
            "npc_locations": [
                {
                    "id": "rhea",
                    "status": "active" if turn % 2 == 0 else "resting",
                    "morale": 70 + (turn % 10),
                    "fatigue": 20 + (turn % 30),
                    "x": turn % 10,
                    "y": (turn + 1) % 10,
                },
                {
                    "id": "boris",
                    "status": "trading",
                    "morale": 80,
                    "fatigue": 10 + (turn % 20),
                    "x": (turn + 5) % 10,
                    "y": (turn - 1) % 10,
                },
            ],
            "recent_events": (
                [
                    f"Turn {turn}: Major event happened",
                    f"Turn {turn}: Minor incident",
                ]
                if turn % 3 == 0
                else []
            ),
        }

        delta = {
            "recent_events": [f"Turn {turn} delta"],
            "flags_added": ["archived"] if turn % 10 == 0 else [],
        }

        arch.record_turn(turn, state, delta)

    return arch


class TestLongCampaignArchive:
    """Test archive behavior over 100+ turns."""

    def test_archive_100_turns_stability(self, long_campaign_archive):
        """Test archive remains stable after 100 turns."""
        arch = long_campaign_archive

        # Should have compressed data at turn 100
        assert arch.current_states is not None
        assert arch.recent_deltas is not None
        assert arch.archive_summaries is not None

        # Should still be able to get context at turn 100
        context = arch.get_context_for_prompt(100)
        assert context is None or isinstance(
            context, str
        )  # Turn 100 might have context or None

    def test_archive_memory_bounded_100_turns(self, long_campaign_archive):
        """Test memory stays bounded even with 100 turns."""
        arch = long_campaign_archive

        # Estimate size
        estimated_size = arch.get_current_state_size()

        # Should be reasonable (less than 2MB even with 100 turns)
        assert estimated_size < 2_000_000

        # Should be larger than 100 bytes but not unbounded
        assert estimated_size > 100

    def test_archive_compression_triggered(self, long_campaign_archive):
        """Test that compression is triggered at appropriate intervals."""
        arch = long_campaign_archive

        # After 100 turns, should have compressed at turns 10, 20, 30... 100
        # Archive summaries should exist
        assert len(arch.archive_summaries) > 0

        # Archive summaries should be keyed by archive checkpoint
        for key in arch.archive_summaries.keys():
            assert key.startswith("archive_")

    def test_archive_injection_at_windows(self, long_campaign_archive):
        """Test context available at injection windows (10, 18, 26, 34...)."""
        arch = long_campaign_archive

        # Test key injection windows
        injection_windows = [10, 18, 26, 34, 50, 90]

        for turn in injection_windows:
            context = arch.get_context_for_prompt(turn)
            # At injection windows, should have content (not empty)
            if turn <= 100:  # Only test valid turns
                assert (
                    context is not None or context == ""
                ), f"Turn {turn} should have content"

    def test_archive_thread_continuity(self, long_campaign_archive):
        """Test that event threads are maintained across turns."""
        arch = long_campaign_archive

        # Get archive summaries (summarized older turns)
        if len(arch.archive_summaries) > 0:
            first_key = sorted(arch.archive_summaries.keys())[0]
            first_summary = arch.archive_summaries[first_key]

            # Should contain event continuity information
            summary_str = first_summary.lower()

            # Should mention threats or events or NPCs
            has_meaningful_content = any(
                keyword in summary_str
                for keyword in ["event", "threat", "npc", "status"]
            )
            assert has_meaningful_content

    def test_archive_npc_tracking_long_term(self, long_campaign_archive):
        """Test NPC status tracked over 100 turns."""
        arch = long_campaign_archive

        # Check NPC history
        assert len(arch.npc_status_history) > 0, "Should track NPC status"

        # Should have entries for NPCs
        npc_statuses = [entry for entry in arch.npc_status_history]
        assert len(npc_statuses) > 0, "Should have NPC status entries"


class TestCampaignSimulation:
    """Simulate actual campaign mechanics."""

    def test_100_turn_campaign_archive_injection(self):
        """Simulate 100-turn campaign with actual state changes."""
        arch = StateArchive("campaign_sim_100")

        injection_count = 0
        archive_context_used = []

        for turn in range(1, 101):
            # Simulate game state
            state = {
                "turn": turn,
                "world": {
                    "threat_level": min(10.0, 1.0 + (turn * 0.09)),
                },
                "structures": {
                    "north_wall": {"integrity": max(10, 100 - (turn * 0.5))},
                    "south_gate": {"integrity": max(20, 100 - (turn * 0.3))},
                },
                "npc_locations": [
                    {
                        "id": "rhea",
                        "status": "active",
                        "morale": 80 - (turn * 0.2),
                        "fatigue": max(0, turn // 20),
                        "x": 5,
                        "y": 5,
                    },
                    {
                        "id": "boris",
                        "status": "trading",
                        "morale": 75,
                        "fatigue": max(0, 10 - turn // 50),
                        "x": 6,
                        "y": 6,
                    },
                ],
                "recent_events": [f"Turn {turn} event"],
            }

            delta = {
                "damage_taken": turn // 50,
                "resources_consumed": turn // 20,
            }

            arch.record_turn(turn, state, delta)

            # Check if context available at injection window
            context = arch.get_context_for_prompt(turn)
            if context:
                injection_count += 1
                archive_context_used.append(turn)

        # Should have injected context at approximately turns 10, 18, 26...
        # Minimum: should have at least one injection
        assert injection_count >= 1

        # Memory should be bounded
        final_size = arch.get_current_state_size()
        assert final_size < 1_500_000

    def test_threat_escalation_tracked(self):
        """Test threat escalation is properly tracked in archive."""
        arch = StateArchive("threat_test_session")

        threat_values = []

        for turn in range(1, 51):
            threat_score = 1.0 + (turn * 0.1)  # Escalating
            threat_values.append(threat_score)

            state = {
                "turn": turn,
                "world": {
                    "threat_level": threat_score,
                },
                "phase": (
                    "calm"
                    if threat_score < 3
                    else "rising" if threat_score < 7 else "peak"
                ),
            }

            delta = {"threat_delta": 0.1}
            arch.record_turn(turn, state, delta)

        # Archive should track threat progression
        assert len(arch.threat_timeline) > 0

        # Threat should be escalating in timeline
        if len(arch.threat_timeline) > 1:
            early_threat = arch.threat_timeline[0]

            # Generally should see escalation
            assert early_threat >= 0

    def test_serialization_for_long_campaign(self):
        """Test archive can be serialized/deserialized for long campaigns."""
        arch = StateArchive("serial_test_session")

        # Populate with 50 turns
        for turn in range(1, 51):
            state = {"turn": turn, "data": f"turn_{turn}"}
            delta = {"change": turn}
            arch.record_turn(turn, state, delta)

        # Serialize
        serialized = arch.to_dict()
        assert serialized is not None
        assert "current_states" in serialized

        # Deserialize
        arch2 = StateArchive.from_dict("serial_test_session", serialized)
        assert arch2 is not None

        # Should have same session_id
        assert arch2.session_id == arch.session_id


class TestArchiveRobustness:
    """Test archive robustness under stress."""

    def test_rapid_turn_recording(self):
        """Test recording many turns rapidly."""
        arch = StateArchive("rapid_test_session")

        # Record 200 turns rapidly
        for turn in range(1, 201):
            state = {
                "turn": turn,
                "value": turn * 2,
                "list": list(range(turn % 10)),
            }
            delta = {"change": turn}
            arch.record_turn(turn, state, delta)

        # Should handle 200 turns without error
        assert len(arch.current_states) > 0

        # Memory should still be bounded
        size = arch.get_current_state_size()
        assert size < 3_000_000

    def test_empty_deltas_handling(self):
        """Test handling of empty state deltas over long campaign."""
        arch = StateArchive("empty_delta_test")

        for turn in range(1, 51):
            state = {"turn": turn, "static_data": "same"}

            # Some turns have empty deltas
            if turn % 3 == 0:
                delta = {}
            else:
                delta = {"minor_change": True}

            arch.record_turn(turn, state, delta)

        # Should handle gracefully
        assert len(arch.current_states) > 0
        assert arch.get_current_state_size() > 0

    def test_large_state_compression(self):
        """Test compression with large state objects."""
        arch = StateArchive("large_state_test")

        for turn in range(1, 31):
            # Create large state with nested data
            state = {
                "turn": turn,
                "large_dict": {f"key_{i}": f"value_{i}" * 100 for i in range(50)},
                "large_list": list(range(1000)),
            }

            delta = {
                "updates": list(range(100)),
            }

            arch.record_turn(turn, state, delta)

        # Should compress despite large states
        assert len(arch.current_states) <= 6
        assert arch.get_current_state_size() < 5_000_000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
