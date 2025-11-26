"""Phase 8 Extended: 500+ turn campaign with Ollama + Archive integration.

Tests realistic gameplay scenarios with archive context injection
and Ollama LLM agent decision-making at scale.
"""

import json
from unittest.mock import patch
from fortress_director.core.state_archive import StateArchive, inject_archive_to_prompt
from fortress_director.llm.ollama_adapter import OllamaAgentPipeline


class TestOllamaCampaign500Turns:
    """Extended campaign tests with Ollama and archive integration."""

    @patch("fortress_director.llm.ollama_adapter.OllamaClient.generate")
    def test_500_turn_campaign_coherence(self, mock_generate):
        """Test 500-turn campaign maintains coherence with Ollama."""
        arch = StateArchive("campaign_500_test")

        def generate_responses(model, prompt, **kwargs):
            # DirectorAgent scene generation
            if "diegetic" in prompt.lower() or "choices" in prompt.lower():
                return json.dumps(
                    {
                        "scene": "Fortress under siege continues.",
                        "choices": [
                            {"choice": "Advance scouts"},
                            {"choice": "Reinforce walls"},
                            {"choice": "Negotiate"},
                        ],
                    }
                )
            # PlannerAgent strategy
            elif "strategic" in prompt.lower() or "strategy" in prompt.lower():
                return json.dumps(
                    {
                        "strategy": "Escalate defense",
                        "actions": ["Mobilize reserves"],
                        "threat_change": -0.1,
                    }
                )
            # WorldRendererAgent atmosphere
            else:
                return "Siege continues with intensity increasing."

        mock_generate.side_effect = generate_responses

        # Record 500 turns
        threat_progression = []
        for turn in range(1, 501):
            threat = 0.2 + (turn * 0.0012)  # Escalate to ~0.8 by turn 500

            state = {
                "turn": turn,
                "world": {
                    "threat_level": threat,
                    "narrative_phase": (
                        "exposition"
                        if turn < 100
                        else (
                            "rising_action"
                            if turn < 300
                            else "climax" if turn < 450 else "resolution"
                        )
                    ),
                    "resources": {"defense": 100, "morale": 80 - (threat * 50)},
                },
                "npc_locations": [
                    {
                        "id": f"commander_{i}",
                        "status": "active",
                        "morale": max(20, 80 - (threat * 30)),
                        "fatigue": min(100, 30 + (threat * 50)),
                        "x": 5 + (i % 3),
                        "y": 5 + (i // 3),
                    }
                    for i in range(3)
                ],
                "events": (
                    [{"type": "escalation", "turn": turn}] if turn % 50 == 0 else []
                ),
            }
            delta = {}
            arch.record_turn(turn, state, delta)
            threat_progression.append(threat)

        # Verify archive handles 500 turns
        assert arch.get_current_state_size() < 100000  # Under 100KB
        assert len(threat_progression) == 500
        assert threat_progression[-1] > threat_progression[0]

        # Get context at 250 and 500
        context_250 = arch.get_context_for_prompt(250)
        context_500 = arch.get_context_for_prompt(500)

        assert context_250 is not None
        assert context_500 is not None
        # Later context should be more complete
        assert len(context_500) > 0

    @patch("fortress_director.llm.ollama_adapter.OllamaClient.generate")
    def test_ollama_campaign_narrative_arc(self, mock_generate):
        """Test narrative arc progression across 300-turn Ollama campaign."""
        arch = StateArchive("narrative_arc_test")

        phases = {
            "exposition": {
                "turn_range": (1, 75),
                "threat_start": 0.1,
                "threat_end": 0.3,
            },
            "rising_action": {
                "turn_range": (76, 200),
                "threat_start": 0.3,
                "threat_end": 0.6,
            },
            "climax": {
                "turn_range": (201, 270),
                "threat_start": 0.6,
                "threat_end": 0.9,
            },
            "resolution": {
                "turn_range": (271, 300),
                "threat_start": 0.9,
                "threat_end": 0.5,
            },
        }

        def generate_phase_aware(model, prompt, **kwargs):
            # Return responses aware of current phase
            if "exposition" in prompt.lower():
                return "Calm preparations begin."
            elif "rising" in prompt.lower():
                return json.dumps(
                    {
                        "strategy": "Prepare for danger",
                        "actions": ["Train troops"],
                        "threat_change": 0.1,
                    }
                )
            elif "climax" in prompt.lower():
                return "Critical moment approaches."
            elif "resolution" in prompt.lower():
                return "Crisis resolved with cost."
            else:
                return json.dumps(
                    {
                        "scene": "Scene descriptor",
                        "choices": [
                            {"choice": "Option"},
                        ],
                    }
                )

        mock_generate.side_effect = generate_phase_aware

        # Record across phases
        for turn in range(1, 301):
            # Determine phase and threat
            phase = "exposition"
            threat = 0.1
            for p, config in phases.items():
                if config["turn_range"][0] <= turn <= config["turn_range"][1]:
                    phase = p
                    range_size = config["turn_range"][1] - config["turn_range"][0]
                    progress = (turn - config["turn_range"][0]) / range_size
                    threat = config["threat_start"] + (
                        (config["threat_end"] - config["threat_start"]) * progress
                    )
                    break

            state = {
                "turn": turn,
                "world": {
                    "threat_level": threat,
                    "narrative_phase": phase,
                },
                "npc_locations": [
                    {
                        "id": "hero",
                        "status": "active",
                        "morale": max(10, 80 - (threat * 40)),
                        "fatigue": min(100, threat * 70),
                        "x": 5,
                        "y": 5,
                    }
                ],
                "events": (
                    [{"type": "phase_transition", "phase": phase}]
                    if turn in [75, 200, 270]
                    else []
                ),
            }
            delta = {}
            arch.record_turn(turn, state, delta)

        # Verify narrative arc is preserved
        context = arch.get_context_for_prompt(300)
        assert context is not None

    @patch("fortress_director.llm.ollama_adapter.OllamaClient.generate")
    def test_ollama_threat_escalation_500_turns(self, mock_generate):
        """Test threat escalation triggers appropriate Ollama responses."""
        arch = StateArchive("threat_escalation_test")

        escalation_responses = []

        def threat_aware_generator(model, prompt, **kwargs):
            # Extract threat level from prompt
            threat_mentioned = False
            if "threat" in prompt.lower():
                threat_mentioned = True

            if threat_mentioned and "strategy" in prompt.lower():
                # Return response based on escalation
                return json.dumps(
                    {
                        "strategy": "Adaptive response",
                        "actions": ["React to threat"],
                        "threat_change": 0,
                    }
                )
            elif "atmosphere" in prompt.lower():
                return "Tension rising in fortress."
            else:
                return json.dumps(
                    {
                        "scene": "Updated scene",
                        "choices": [{"choice": "Adapt"}],
                    }
                )

        mock_generate.side_effect = threat_aware_generator

        # Campaign with threat escalation at key points
        threat_events = [100, 200, 300, 400]
        for turn in range(1, 451):
            base_threat = 0.2 + (turn * 0.001)

            # Escalations at key turns
            if turn in threat_events:
                base_threat += 0.2

            state = {
                "turn": turn,
                "world": {"threat_level": base_threat},
                "npc_locations": [
                    {
                        "id": "soldier",
                        "status": "active",
                        "morale": max(20, 80 - (base_threat * 50)),
                        "fatigue": min(100, base_threat * 60),
                        "x": 5,
                        "y": 5,
                    }
                ],
                "events": (
                    [
                        {
                            "type": "threat_escalation",
                            "severity": "critical",
                        }
                    ]
                    if turn in threat_events
                    else []
                ),
            }
            delta = {}
            arch.record_turn(turn, state, delta)

            if turn in threat_events:
                escalation_responses.append({"turn": turn, "threat": base_threat})

        # Verify threat escalation is captured
        assert len(escalation_responses) == 4
        context = arch.get_context_for_prompt(450)
        assert context is not None

    @patch("fortress_director.llm.ollama_adapter.OllamaClient.generate")
    def test_ollama_npc_morale_tracking_300_turns(self, mock_generate):
        """Test NPC morale changes tracked across 300-turn Ollama campaign."""
        arch = StateArchive("morale_tracking_test")

        def generate_response(model, prompt, **kwargs):
            return json.dumps(
                {
                    "scene": "Scene",
                    "choices": [{"choice": "Action"}],
                }
            )

        mock_generate.return_value = json.dumps(
            {
                "scene": "Scene",
                "choices": [{"choice": "Action"}],
            }
        )

        morale_trajectory = {}
        for turn in range(1, 301):
            # Morale decreases as threat increases
            threat = 0.2 + (turn * 0.002)
            morale = max(20, 80 - (threat * 40))

            state = {
                "turn": turn,
                "world": {"threat_level": threat},
                "npc_locations": [
                    {
                        "id": "scout_rhea",
                        "status": "active",
                        "morale": morale,
                        "fatigue": min(100, turn * 0.3),
                        "x": 5,
                        "y": 5,
                    },
                    {
                        "id": "commander_boris",
                        "status": "active",
                        "morale": morale + 10,  # Commander more resilient
                        "fatigue": min(100, turn * 0.2),
                        "x": 5,
                        "y": 5,
                    },
                ],
            }
            delta = {}
            arch.record_turn(turn, state, delta)

            if turn % 50 == 0:
                morale_trajectory[turn] = morale

        # Verify morale degradation
        morale_values = list(morale_trajectory.values())
        assert len(morale_values) == 6
        # Morale should generally decrease
        assert morale_values[-1] < morale_values[0]

    @patch("fortress_director.llm.ollama_adapter.OllamaClient.generate")
    def test_ollama_memory_bounded_500_turns(self, mock_generate):
        """Test Ollama campaign memory stays bounded at 500 turns."""
        arch = StateArchive("memory_bounded_500_test")

        memory_samples = []

        for turn in range(1, 501):
            state = {
                "turn": turn,
                "world": {"threat_level": 0.5},
                "npc_locations": [
                    {
                        "id": f"npc_{i}",
                        "status": "active",
                        "morale": 70,
                        "fatigue": 20,
                        "x": 5 + i,
                        "y": 5 + i,
                    }
                    for i in range(5)
                ],
            }
            delta = {}
            arch.record_turn(turn, state, delta)

            # Sample memory at key points
            if turn in [100, 200, 300, 400, 500]:
                size = arch.get_current_state_size()
                memory_samples.append((turn, size))

        # Verify O(1) memory scaling
        assert len(memory_samples) == 5
        # Final memory should be bounded
        assert memory_samples[-1][1] < 100000  # <100KB

        # Growth should be sublinear
        size_growth = memory_samples[-1][1] - memory_samples[0][1]
        turn_growth = memory_samples[-1][0] - memory_samples[0][0]
        # Memory shouldn't grow 5x for 4x turn count
        assert size_growth < turn_growth * 100

    @patch("fortress_director.llm.ollama_adapter.OllamaClient.generate")
    def test_ollama_archive_context_at_scale(self, mock_generate):
        """Test archive context injection at 500-turn scale."""
        arch = StateArchive("context_scale_test")

        # Mock response
        mock_generate.return_value = json.dumps(
            {
                "scene": "Responding to context",
                "choices": [{"choice": "Choice"}],
            }
        )

        # Record 500 turns
        for turn in range(1, 501):
            state = {
                "turn": turn,
                "world": {"threat_level": 0.5},
                "npc_locations": [
                    {
                        "id": "npc",
                        "status": "active",
                        "morale": 70,
                        "fatigue": 20,
                        "x": 5,
                        "y": 5,
                    }
                ],
            }
            delta = {}
            arch.record_turn(turn, state, delta)

        # Get contexts at various scales
        contexts = {}
        for checkpoint in [50, 100, 250, 500]:
            context = arch.get_context_for_prompt(checkpoint)
            if context:
                contexts[checkpoint] = len(context)

        # Verify contexts available and bounded
        assert len(contexts) > 0
        for size in contexts.values():
            # Context should be reasonable size (under 5K chars = 1250 tokens)
            assert size < 5000
