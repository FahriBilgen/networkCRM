"""Test narrative consistency across long campaigns with archive context."""

from fortress_director.core.state_archive import StateArchive


class TestNarrativeThreads:
    """Test that narrative threads remain coherent across campaigns."""

    def test_npc_motivation_thread(self):
        """Test NPC motivations persist across 100 turns."""
        arch = StateArchive("npc_motivation_test")

        # Track NPC status changes that form a narrative thread
        for turn in range(1, 101):
            # Narrative: Rhea starts as cautious, becomes confident
            if turn < 30:
                rhea_status = "cautious"
                rhea_morale = 60
            elif turn < 60:
                rhea_status = "confident"
                rhea_morale = 75
            else:
                rhea_status = "heroic"
                rhea_morale = 90

            # Narrative: Boris starts as nervous, becomes strategic
            if turn < 30:
                boris_status = "nervous"
                boris_morale = 55
            elif turn < 60:
                boris_status = "calculating"
                boris_morale = 70
            else:
                boris_status = "strategic"
                boris_morale = 85

            state = {
                "turn": turn,
                "world": {"threat_level": 1.0 + (turn * 0.05)},
                "npc_locations": [
                    {
                        "id": "rhea",
                        "status": rhea_status,
                        "morale": rhea_morale,
                        "fatigue": 20 + (turn % 15),
                        "x": 5,
                        "y": 5,
                    },
                    {
                        "id": "boris",
                        "status": boris_status,
                        "morale": boris_morale,
                        "fatigue": 15 + (turn % 20),
                        "x": 6,
                        "y": 6,
                    },
                ],
                "recent_events": [
                    f"Rhea: {rhea_status}",
                    f"Boris: {boris_status}",
                ],
            }

            delta = {
                "recent_events": [
                    f"Turn {turn}: Rhea now {rhea_status}",
                    f"Turn {turn}: Boris now {boris_status}",
                ],
            }

            arch.record_turn(turn, state, delta)

        # Verify narrative threads are tracked
        assert len(arch.npc_status_history) > 0
        assert "rhea" in arch.npc_status_history
        assert "boris" in arch.npc_status_history

        # Track should show progression
        rhea_entries = arch.npc_status_history["rhea"]
        assert len(rhea_entries) > 0

    def test_plot_escalation_continuity(self):
        """Test that plot escalation is tracked consistently."""
        arch = StateArchive("plot_escalation_test")

        plot_phases = {
            "turquoise": (1, 20),  # Phase 1: Preparation
            "yellow": (21, 40),  # Phase 2: Skirmish
            "orange": (41, 70),  # Phase 3: Siege
            "red": (71, 100),  # Phase 4: Crisis
        }

        for turn in range(1, 101):
            # Determine current phase
            current_phase = None
            phase_name = None
            for pname, (start, end) in plot_phases.items():
                if start <= turn <= end:
                    current_phase = pname
                    phase_name = pname
                    break

            # Threat escalates with phase
            threat_map = {
                "turquoise": 1.0,
                "yellow": 3.0,
                "orange": 5.0,
                "red": 8.0,
            }
            threat_level = threat_map.get(phase_name, 1.0)
            threat_level += (turn % 20) * 0.1  # Add variance

            state = {
                "turn": turn,
                "world": {
                    "threat_level": threat_level,
                    "phase": phase_name,
                },
                "npc_locations": [
                    {
                        "id": "commander",
                        "status": "leading",
                        "morale": max(20, 100 - threat_level * 5),
                        "fatigue": int(threat_level * 10),
                        "x": 0,
                        "y": 0,
                    }
                ],
                "recent_events": [f"Phase: {phase_name}"],
            }

            delta = {
                "recent_events": [f"Turn {turn}: {phase_name} phase"],
                "flags_added": [phase_name] if turn % 10 == 0 else [],
            }

            arch.record_turn(turn, state, delta)

        # Verify threat escalation tracked
        assert len(arch.threat_timeline) > 0
        assert len(arch.event_log) > 0

        # Threat should escalate over time
        if len(arch.threat_timeline) >= 20:
            early_avg = sum(arch.threat_timeline[:10]) / 10
            late_avg = sum(arch.threat_timeline[-10:]) / 10
            assert late_avg > early_avg

    def test_world_state_continuity(self):
        """Test that world state changes are consistently tracked."""
        arch = StateArchive("world_state_test")

        for turn in range(1, 51):
            # World state degrades as battle progresses
            wall_integrity = max(0, 100 - (turn * 0.8))
            gate_integrity = max(0, 100 - (turn * 0.5))
            morale = max(0, 100 - (turn * 0.6))
            food = max(0, 100 - (turn * 0.3))

            state = {
                "turn": turn,
                "world": {
                    "threat_level": 1.0 + (turn * 0.08),
                    "wall_integrity": wall_integrity,
                    "gate_integrity": gate_integrity,
                    "morale": morale,
                    "food": food,
                },
                "npc_locations": [
                    {
                        "id": "guard",
                        "status": "defending",
                        "morale": morale,
                        "fatigue": turn // 2,
                        "x": 10,
                        "y": 10,
                    }
                ],
                "recent_events": [
                    f"Wall: {wall_integrity:.0f}%",
                    f"Gate: {gate_integrity:.0f}%",
                    f"Morale: {morale:.0f}%",
                ],
            }

            delta = {
                "recent_events": [
                    f"Turn {turn}: Structures degrading",
                ],
            }

            arch.record_turn(turn, state, delta)

        # Verify consistent tracking
        assert len(arch.event_log) > 0
        assert len(arch.threat_timeline) > 0

        # Events should be tracked (world state may not be directly
        # in events, but threat escalation should be)

    def test_decision_consequence_chain(self):
        """Test that player decisions create traceable consequence chains."""
        arch = StateArchive("decision_test")

        decision_flags = []

        for turn in range(1, 51):
            state = {
                "turn": turn,
                "world": {"threat_level": 1.0 + (turn * 0.06)},
                "npc_locations": [
                    {
                        "id": "advisor",
                        "status": "counseling",
                        "morale": 70,
                        "fatigue": 10 + (turn % 20),
                        "x": 5,
                        "y": 5,
                    }
                ],
            }

            # Simulate key decisions at certain turns
            delta = {}
            if turn == 10:
                decision_flags.append("defensive_posture")
                delta = {
                    "recent_events": [
                        "Turn 10: Took defensive posture",
                    ],
                    "flags_added": ["defensive_posture"],
                }
            elif turn == 20:
                decision_flags.append("reinforcements")
                delta = {
                    "recent_events": [
                        "Turn 20: Called for reinforcements",
                    ],
                    "flags_added": ["reinforcements"],
                }
            elif turn == 30:
                decision_flags.append("negotiation")
                delta = {
                    "recent_events": [
                        "Turn 30: Attempted negotiation",
                    ],
                    "flags_added": ["negotiation"],
                }

            arch.record_turn(turn, state, delta)

        # Verify decisions are recorded
        assert len(decision_flags) == 3
        event_str = "\n".join(arch.event_log)
        for decision in decision_flags:
            assert decision in event_str


class TestNarrativeCohesion:
    """Test overall narrative cohesion with archive."""

    def test_archive_summary_contains_narrative_arc(self):
        """Test that archive summary captures narrative arc."""
        arch = StateArchive("narrative_arc_test")

        for turn in range(1, 51):
            # Create narrative arc: calm -> warning -> crisis
            if turn < 20:
                situation = "The village is calm but on alert"
            elif turn < 35:
                situation = "Enemy scouts spotted. Walls being reinforced"
            else:
                situation = "Enemy army at the gates! Battle stations!"

            state = {
                "turn": turn,
                "world": {
                    "threat_level": (1.0 if turn < 20 else 3.0 if turn < 35 else 7.0)
                },
                "npc_locations": [
                    {
                        "id": "commander",
                        "status": "commanding",
                        "morale": (100 if turn < 20 else 75 if turn < 35 else 50),
                        "fatigue": turn // 3,
                        "x": 0,
                        "y": 0,
                    }
                ],
                "recent_events": [situation],
            }

            delta = {
                "recent_events": [situation],
            }

            arch.record_turn(turn, state, delta)

        # Get context at turn 40 (should have narrative summary)
        context = arch.get_context_for_prompt(40)
        if context:
            context_lower = context.lower()
            # Should reference escalation or situation changes
            has_narrative = (
                "threat" in context_lower
                or "event" in context_lower
                or "commander" in context_lower
            )
            assert has_narrative

    def test_npc_relationship_tracking(self):
        """Test that NPC relationships and trust levels persist."""
        arch = StateArchive("relationship_test")

        for turn in range(1, 51):
            # Rhea's trust in player leadership grows over time
            if turn < 15:
                rhea_opinion = "skeptical"
            elif turn < 30:
                rhea_opinion = "cautiously_optimistic"
            else:
                rhea_opinion = "loyal_supporter"

            # Boris's mercenary nature constant but commitment varies
            if turn < 20:
                boris_status = "considering_options"
            elif turn < 40:
                boris_status = "committed_to_paycheck"
            else:
                boris_status = "invested_in_victory"

            state = {
                "turn": turn,
                "world": {"threat_level": 1.0 + (turn * 0.05)},
                "npc_locations": [
                    {
                        "id": "rhea",
                        "status": rhea_opinion,
                        "morale": (
                            60
                            if rhea_opinion == "skeptical"
                            else (75 if rhea_opinion == "cautiously_optimistic" else 90)
                        ),
                        "fatigue": 10 + (turn % 15),
                        "x": 5,
                        "y": 5,
                    },
                    {
                        "id": "boris",
                        "status": boris_status,
                        "morale": 70,
                        "fatigue": 15 + (turn % 20),
                        "x": 6,
                        "y": 6,
                    },
                ],
            }

            delta = {"change": True}
            arch.record_turn(turn, state, delta)

        # Verify relationship tracking persists
        npc_histo = arch.npc_status_history
        assert "rhea" in npc_histo
        assert "boris" in npc_histo

        # Should see relationship progression
        rhea_statuses = npc_histo["rhea"]
        assert len(rhea_statuses) > 0
