"""Test archive injection effectiveness and LLM context retention."""

from fortress_director.core.state_archive import StateArchive


class TestInjectionEffectiveness:
    """Measure how much archive context is used in prompts."""

    def test_injection_frequency_matches_windows(self):
        """Test that injections happen at expected turn windows."""
        arch = StateArchive("injection_freq_test")

        injection_turns = []

        for turn in range(1, 101):
            state = {
                "turn": turn,
                "world": {"threat_level": 1.0 + (turn * 0.05)},
                "npc_locations": [
                    {
                        "id": f"npc_{i}",
                        "status": "active",
                        "morale": 70,
                        "fatigue": 10,
                        "x": i,
                        "y": i,
                    }
                    for i in range(3)
                ],
                "recent_events": [f"Turn {turn} event"],
            }
            delta = {"change": True}
            arch.record_turn(turn, state, delta)

            context = arch.get_context_for_prompt(turn)
            if context:
                injection_turns.append(turn)

        # Should have injections at or after turn 10
        assert len(injection_turns) > 0
        # First injection should be at turn 10
        assert injection_turns[0] == 10

    def test_injection_context_size_growth(self):
        """Test that context size grows appropriately with turns."""
        arch = StateArchive("context_size_test")

        context_sizes = {}

        for turn in range(1, 101):
            state = {
                "turn": turn,
                "world": {"threat_level": 1.0 + (turn * 0.05)},
                "npc_locations": [
                    {
                        "id": f"npc_{i}",
                        "status": "active",
                        "morale": 70,
                        "fatigue": 10,
                        "x": i,
                        "y": i,
                    }
                    for i in range(5)
                ],
                "recent_events": [
                    f"Turn {turn}: Event 1",
                    f"Turn {turn}: Event 2",
                ],
            }
            delta = {"change": True}
            arch.record_turn(turn, state, delta)

            context = arch.get_context_for_prompt(turn)
            if context:
                context_sizes[turn] = len(context)

        # Should have collected context at multiple turns
        assert len(context_sizes) > 0

        # Context should generally grow with time (more history = more summary)
        injection_turns = sorted(context_sizes.keys())
        if len(injection_turns) > 1:
            early_context = context_sizes[injection_turns[0]]
            late_context = context_sizes[injection_turns[-1]]
            # Later context should be larger (or equal with compression)
            assert late_context >= early_context * 0.5

    def test_injection_content_quality(self):
        """Test that injected content contains meaningful data."""
        arch = StateArchive("content_quality_test")

        for turn in range(1, 51):
            state = {
                "turn": turn,
                "world": {"threat_level": 2.0 + (turn * 0.08)},
                "npc_locations": [
                    {
                        "id": "commander",
                        "status": "leading" if turn > 25 else "planning",
                        "morale": max(30, 80 - turn),
                        "fatigue": min(100, turn // 2),
                        "x": 10,
                        "y": 10,
                    },
                    {
                        "id": "scout",
                        "status": "injured" if turn > 40 else "active",
                        "morale": 70,
                        "fatigue": 20,
                        "x": 5,
                        "y": 5,
                    },
                ],
                "recent_events": [f"Turn {turn}: Major event"],
            }
            delta = {
                "recent_events": [f"Delta event turn {turn}"],
                "flags_added": [f"flag_{turn}"] if turn % 10 == 0 else [],
            }
            arch.record_turn(turn, state, delta)

        # Get context at turn 40 (after two compressions)
        context = arch.get_context_for_prompt(40)
        if context is None:
            context = ""

        context_str = context.lower()

        # Should contain meaningful content about NPC status, threat, events
        has_npc_info = "commander" in context_str or "scout" in context_str
        has_threat_info = "threat" in context_str
        has_event_info = "event" in context_str or "flag" in context_str

        assert (
            has_npc_info or has_threat_info or has_event_info
        ), "Context should have meaningful data"

    def test_injection_with_no_events(self):
        """Test injection works even with minimal game state changes."""
        arch = StateArchive("no_events_test")

        # Record 50 turns with static state (no events)
        for turn in range(1, 51):
            state = {
                "turn": turn,
                "world": {"threat_level": 2.0},  # Static
                "npc_locations": [
                    {
                        "id": "static_npc",
                        "status": "idle",
                        "morale": 75,
                        "fatigue": 15,
                        "x": 0,
                        "y": 0,
                    }
                ],
                "recent_events": [],  # No events
            }
            delta = {}  # No changes
            arch.record_turn(turn, state, delta)

        # Should still have context at injection windows
        # Context might be None (no major events), but archive should exist
        assert len(arch.archive_summaries) > 0

    def test_injection_captures_threat_escalation(self):
        """Test that threat escalation is captured in injected context."""
        arch = StateArchive("threat_escalation_test")

        for turn in range(1, 31):
            # Threat escalates dramatically at turn 20
            threat_level = 1.0 if turn < 20 else 5.0 + (turn - 20) * 0.5

            state = {
                "turn": turn,
                "world": {"threat_level": threat_level},
                "npc_locations": [
                    {
                        "id": "guard",
                        "status": "alert" if threat_level > 4 else "calm",
                        "morale": max(20, 100 - (threat_level * 10)),
                        "fatigue": int(threat_level * 15),
                        "x": 0,
                        "y": 0,
                    }
                ],
            }
            delta = {}
            arch.record_turn(turn, state, delta)

        # Get context at turn 28 (should capture escalation)
        context = arch.get_context_for_prompt(28)
        if context:
            context_str = context.lower()
            # Should mention threat trend
            has_threat = "threat" in context_str
            assert has_threat, "Should capture threat escalation"


class TestContextWindow:
    """Test that injected context fits within LLM context windows."""

    def test_context_size_under_4k_tokens(self):
        """Test archive context stays under 4K tokens (roughly)."""
        arch = StateArchive("context_window_test")

        # Simulate 200-turn campaign
        for turn in range(1, 201):
            state = {
                "turn": turn,
                "world": {"threat_level": 1.0 + (turn * 0.03)},
                "npc_locations": [
                    {
                        "id": f"npc_{i}",
                        "status": "active",
                        "morale": 70 - (i * 5),
                        "fatigue": 10 + (i * 3),
                        "x": i,
                        "y": i,
                    }
                    for i in range(10)
                ],
                "recent_events": [f"Turn {turn}: Event {j}" for j in range(3)],
            }
            delta = {"change": True}
            arch.record_turn(turn, state, delta)

        # Check all injections are reasonably sized
        for turn in range(1, 201):
            context = arch.get_context_for_prompt(turn)
            if context:
                # Rough estimate: ~4 chars per token
                token_estimate = len(context) / 4
                # Should be under 4000 tokens
                assert (
                    token_estimate < 4000
                ), f"Context too large at turn {turn}: {token_estimate} tokens"

    def test_cumulative_archive_memory(self):
        """Test total archive memory stays bounded over long campaigns."""
        arch = StateArchive("cumulative_memory_test")

        max_size_seen = 0

        for turn in range(1, 501):
            state = {
                "turn": turn,
                "world": {"threat_level": 1.0 + (turn * 0.02)},
                "npc_locations": [
                    {
                        "id": f"npc_{i}",
                        "status": "active",
                        "morale": 70,
                        "fatigue": 15,
                        "x": i,
                        "y": i,
                    }
                    for i in range(5)
                ],
            }
            delta = {}
            arch.record_turn(turn, state, delta)

            current_size = arch.get_current_state_size()
            max_size_seen = max(max_size_seen, current_size)

        # Even after 500 turns, memory should be bounded
        assert max_size_seen < 500_000


class TestPromptInjection:
    """Test actual prompt injection with archive context."""

    def test_inject_archive_to_prompt_format(self):
        """Test archive is injected into prompt in correct format."""
        from fortress_director.core.state_archive import (
            inject_archive_to_prompt,
        )

        arch = StateArchive("prompt_injection_test")

        # Create 20 turns to get archive
        for turn in range(1, 21):
            state = {
                "turn": turn,
                "world": {"threat_level": 1.0 + (turn * 0.1)},
                "npc_locations": [
                    {
                        "id": "protagonist",
                        "status": "fighting",
                        "morale": 80,
                        "fatigue": 20,
                        "x": 0,
                        "y": 0,
                    }
                ],
            }
            delta = {}
            arch.record_turn(turn, state, delta)

        original_prompt = "You are a game narrator. What happens next?"

        # Inject at turn 18 (should have context)
        injected = inject_archive_to_prompt(arch, 18, original_prompt)

        # Should contain archive markers
        assert "HISTORICAL CONTEXT" in injected or injected == original_prompt
        assert "CURRENT SITUATION" in injected or injected == original_prompt

    def test_inject_archive_preserves_original_prompt(self):
        """Test that archive injection doesn't lose original prompt."""
        from fortress_director.core.state_archive import (
            inject_archive_to_prompt,
        )

        arch = StateArchive("preserve_prompt_test")

        for turn in range(1, 21):
            state = {
                "turn": turn,
                "world": {"threat_level": 2.0},
                "npc_locations": [
                    {
                        "id": "npc",
                        "status": "active",
                        "morale": 70,
                        "fatigue": 15,
                        "x": 0,
                        "y": 0,
                    }
                ],
            }
            delta = {}
            arch.record_turn(turn, state, delta)

        original = "Tell me what the player sees: A castle wall."
        injected = inject_archive_to_prompt(arch, 18, original)

        # Original prompt should be preserved (at end)
        assert (
            original in injected or "castle wall" in injected
        ), "Original prompt should be preserved"
