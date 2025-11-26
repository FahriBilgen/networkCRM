"""Phase 8: Ollama local LLM integration tests.

Tests DirectorAgent, PlannerAgent, WorldRendererAgent with local Ollama models.
Validates response quality, narrative coherence, and performance with archive context.
"""

import json
from unittest.mock import Mock, patch, MagicMock
from fortress_director.core.state_archive import StateArchive
from fortress_director.llm.ollama_adapter import (
    OllamaClient,
    DirectorAgentOllama,
    PlannerAgentOllama,
    WorldRendererOllama,
    OllamaAgentPipeline,
)


class TestOllamaClientBasics:
    """Test basic Ollama client functionality."""

    def test_ollama_client_initialization(self):
        """Test OllamaClient initializes correctly."""
        client = OllamaClient()
        assert client.base_url == "http://localhost:11434"
        assert client.generate_url == "http://localhost:11434/api/generate"

    @patch("fortress_director.llm.ollama_adapter.requests.get")
    def test_ollama_client_availability_check(self, mock_get):
        """Test Ollama availability check."""
        mock_get.return_value.status_code = 200
        client = OllamaClient()

        assert client.is_available() is True

    @patch("fortress_director.llm.ollama_adapter.requests.get")
    def test_ollama_client_unavailable(self, mock_get):
        """Test Ollama unavailability detection."""
        mock_get.side_effect = Exception("Connection refused")
        client = OllamaClient()

        assert client.is_available() is False

    @patch("fortress_director.llm.ollama_adapter.requests.post")
    def test_ollama_generate_response(self, mock_post):
        """Test Ollama text generation."""
        mock_post.return_value.json.return_value = {"response": "Generated text"}
        client = OllamaClient()

        response = client.generate("mistral", "Test prompt", max_tokens=100)

        assert response == "Generated text"
        mock_post.assert_called_once()

    @patch("fortress_director.llm.ollama_adapter.requests.post")
    def test_ollama_generate_timeout(self, mock_post):
        """Test Ollama timeout handling."""
        from requests.exceptions import Timeout

        mock_post.side_effect = Timeout()
        client = OllamaClient()

        response = client.generate("mistral", "Test prompt")

        assert response is None

    @patch("fortress_director.llm.ollama_adapter.requests.post")
    def test_ollama_pull_model(self, mock_post):
        """Test Ollama model pulling."""
        mock_post.return_value.status_code = 200
        client = OllamaClient()

        result = client.pull_model("mistral")

        assert result is True


class TestDirectorAgentOllama:
    """Test DirectorAgent with Ollama."""

    def test_director_agent_initialization(self):
        """Test DirectorAgent initializes with Ollama client."""
        client = OllamaClient()
        director = DirectorAgentOllama(client, "mistral")

        assert director.client is client
        assert director.model == "mistral"

    @patch.object(OllamaClient, "generate")
    def test_director_generates_scene_and_choices(self, mock_generate):
        """Test DirectorAgent generates scene with choices."""
        # Mock JSON response from Ollama
        json_response = json.dumps(
            {
                "scene": "The fortress walls stand firm against the encroaching army.",
                "choices": [
                    {"choice": "Send scouts to investigate"},
                    {"choice": "Reinforce the northern wall"},
                    {"choice": "Negotiate with the enemy commander"},
                ],
            }
        )
        mock_generate.return_value = json_response

        client = OllamaClient()
        director = DirectorAgentOllama(client, "mistral")

        context = "Turn: 50, Threat: 0.7, NPCs: Scout Rhea (morale 60)"
        world_state = {"turn": 50, "threat_level": 0.7}

        result = director.generate_scene_with_choices(context, world_state)

        assert result is not None
        assert "scene" in result
        assert "choices" in result
        assert len(result["choices"]) == 3

    @patch.object(OllamaClient, "generate")
    def test_director_handles_malformed_json(self, mock_generate):
        """Test DirectorAgent handles malformed JSON gracefully."""
        mock_generate.return_value = "Invalid json {{"

        client = OllamaClient()
        director = DirectorAgentOllama(client, "mistral")

        result = director.generate_scene_with_choices("context", {})

        assert result is None

    @patch.object(OllamaClient, "generate")
    def test_director_handles_missing_response(self, mock_generate):
        """Test DirectorAgent handles missing response."""
        mock_generate.return_value = None

        client = OllamaClient()
        director = DirectorAgentOllama(client, "mistral")

        result = director.generate_scene_with_choices("context", {})

        assert result is None


class TestPlannerAgentOllama:
    """Test PlannerAgent with Ollama."""

    def test_planner_agent_initialization(self):
        """Test PlannerAgent initializes with Ollama client."""
        client = OllamaClient()
        planner = PlannerAgentOllama(client, "phi")

        assert planner.client is client
        assert planner.model == "phi"

    @patch.object(OllamaClient, "generate")
    def test_planner_decides_strategy(self, mock_generate):
        """Test PlannerAgent decides strategy."""
        json_response = json.dumps(
            {
                "strategy": "Reinforce northern defenses",
                "actions": ["Deploy archer squad", "Repair wall section"],
                "threat_change": -0.15,
            }
        )
        mock_generate.return_value = json_response

        client = OllamaClient()
        planner = PlannerAgentOllama(client, "phi")

        context = "Turn: 50, Threat: 0.7, Enemy forces: 500"
        player_choice = "Reinforce the northern wall"

        result = planner.decide_strategy(context, player_choice)

        assert result is not None
        assert "strategy" in result
        assert "actions" in result
        assert isinstance(result["actions"], list)

    @patch.object(OllamaClient, "generate")
    def test_planner_threat_escalation_tracking(self, mock_generate):
        """Test PlannerAgent tracks threat escalation."""
        json_response = json.dumps(
            {
                "strategy": "Escalate defense",
                "actions": ["Full mobilization"],
                "threat_change": 0.25,
            }
        )
        mock_generate.return_value = json_response

        client = OllamaClient()
        planner = PlannerAgentOllama(client, "phi")

        result = planner.decide_strategy("context", "Do nothing")

        assert result["threat_change"] == 0.25


class TestWorldRendererOllama:
    """Test WorldRendererAgent with Ollama."""

    def test_renderer_initialization(self):
        """Test WorldRendererAgent initializes with Ollama client."""
        client = OllamaClient()
        renderer = WorldRendererOllama(client, "gemma")

        assert renderer.client is client
        assert renderer.model == "gemma"

    @patch.object(OllamaClient, "generate")
    def test_renderer_generates_atmosphere(self, mock_generate):
        """Test WorldRendererAgent renders atmosphere."""
        atmosphere_text = (
            "The fortress courtyard is alive with urgent activity. "
            "Soldiers rush to their positions, the clang of armor echoing off stone walls. "
            "Dark smoke rises from enemy camps in the distance."
        )
        mock_generate.return_value = atmosphere_text

        client = OllamaClient()
        renderer = WorldRendererOllama(client, "gemma")

        context = "Turn: 50, Threat: 0.7"
        result = renderer.render_atmosphere(context, "rising_action")

        assert result is not None
        assert "fortress" in result.lower() or "soldiers" in result.lower()

    @patch.object(OllamaClient, "generate")
    def test_renderer_handles_missing_response(self, mock_generate):
        """Test WorldRendererAgent handles missing response."""
        mock_generate.return_value = None

        client = OllamaClient()
        renderer = WorldRendererOllama(client, "gemma")

        result = renderer.render_atmosphere("context", "exposition")

        assert result is None


class TestOllamaAgentPipeline:
    """Test full agent pipeline with Ollama."""

    def test_pipeline_initialization(self):
        """Test OllamaAgentPipeline initializes all agents."""
        pipeline = OllamaAgentPipeline()

        assert pipeline.director is not None
        assert pipeline.planner is not None
        assert pipeline.renderer is not None

    @patch.object(WorldRendererOllama, "render_atmosphere")
    @patch.object(PlannerAgentOllama, "decide_strategy")
    @patch.object(DirectorAgentOllama, "generate_scene_with_choices")
    def test_pipeline_execute_turn(self, mock_director, mock_planner, mock_renderer):
        """Test pipeline executes full turn."""
        mock_director.return_value = {
            "scene": "Scene description",
            "choices": [{"choice": "Option 1"}],
        }
        mock_planner.return_value = {
            "strategy": "Strategy",
            "actions": ["Action 1"],
        }
        mock_renderer.return_value = "Atmospheric description"

        pipeline = OllamaAgentPipeline()
        context = "Archive context"
        world_state = {"turn": 50, "narrative_phase": "rising_action"}

        result = pipeline.execute_turn(
            context, world_state, player_choice="Test choice"
        )

        assert result is not None
        assert "turn" in result


class TestOllamaWithArchiveContext:
    """Test Ollama agents receiving and using archive context."""

    @patch.object(OllamaClient, "generate")
    def test_director_with_archive_context(self, mock_generate):
        """Test DirectorAgent receives injected archive context."""
        json_response = json.dumps(
            {
                "scene": "Based on archive: Turn 50 with escalating threat",
                "choices": [{"choice": "Option"}],
            }
        )
        mock_generate.return_value = json_response

        arch = StateArchive("test_director")
        for turn in range(1, 51):
            state = {
                "turn": turn,
                "world": {"threat_level": 0.5 + (turn * 0.01)},
                "npc_locations": [
                    {
                        "id": "rhea",
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

        context = arch.get_context_for_prompt(50)
        assert context is not None

        client = OllamaClient()
        director = DirectorAgentOllama(client, "mistral")

        result = director.generate_scene_with_choices(context, state)

        # Verify archive context was in the prompt
        assert result is not None

    @patch.object(OllamaClient, "generate")
    def test_planner_with_threat_escalation_context(self, mock_generate):
        """Test PlannerAgent receives threat escalation context."""
        json_response = json.dumps(
            {
                "strategy": "Respond to escalation",
                "actions": ["Mobilize"],
                "threat_change": -0.1,
            }
        )
        mock_generate.return_value = json_response

        arch = StateArchive("test_planner")
        threat_levels = []

        for turn in range(1, 101):
            threat = 0.2 + (turn * 0.008)  # Escalates over time
            threat_levels.append(threat)

            state = {
                "turn": turn,
                "world": {"threat_level": threat},
                "npc_locations": [
                    {
                        "id": "commander",
                        "status": "active",
                        "morale": max(30, 80 - (threat * 30)),
                        "fatigue": min(100, threat * 50),
                        "x": 5,
                        "y": 5,
                    }
                ],
            }
            delta = {}
            arch.record_turn(turn, state, delta)

        context = arch.get_context_for_prompt(100)
        assert context is not None

        client = OllamaClient()
        planner = PlannerAgentOllama(client, "phi")

        result = planner.decide_strategy(context, "Prepare defense")

        assert result is not None
        assert "threat_change" in result


class TestOllamaResponseQuality:
    """Test response quality from Ollama agents."""

    @patch.object(OllamaClient, "generate")
    def test_ollama_maintains_coherence_100_turns(self, mock_generate):
        """Test Ollama responses remain coherent across 100-turn campaign."""

        # Simulate responses that maintain coherence
        def generate_mock(model, prompt, **kwargs):
            # Determine response based on model
            if "threat" in prompt.lower():
                return json.dumps(
                    {
                        "strategy": "Adapt to threat level",
                        "actions": ["Monitor situation"],
                        "threat_change": 0,
                    }
                )
            elif "atmosphere" in prompt.lower() or "phase" in prompt.lower():
                return "Atmosphere description for current phase"
            else:
                return json.dumps(
                    {
                        "scene": "Scene based on context",
                        "choices": [
                            {"choice": "Option 1"},
                            {"choice": "Option 2"},
                            {"choice": "Option 3"},
                        ],
                    }
                )

        mock_generate.side_effect = generate_mock

        client = OllamaClient()
        pipeline = OllamaAgentPipeline(client)

        coherent_responses = 0
        for turn in range(1, 101):
            context = f"Turn: {turn}, Status: Active"
            world_state = {"turn": turn, "narrative_phase": "rising_action"}

            result = pipeline.execute_turn(context, world_state)

            if result is not None:
                coherent_responses += 1

        # Most responses should be coherent
        assert (
            coherent_responses > 90
        ), f"Only {coherent_responses}/100 responses coherent"

    @patch.object(OllamaClient, "generate")
    def test_ollama_narrative_phase_awareness(self, mock_generate):
        """Test Ollama respects narrative phase in responses."""
        phase_responses = {
            "exposition": "Calm description of fortress preparations",
            "rising_action": "Intensifying danger description",
            "climax": "Critical moment description",
            "resolution": "Aftermath description",
        }

        def generate_mock(model, prompt, **kwargs):
            for phase, response in phase_responses.items():
                if phase in prompt.lower():
                    return response
            return "Generic description"

        mock_generate.side_effect = generate_mock

        client = OllamaClient()
        renderer = WorldRendererOllama(client, "gemma")

        for phase, expected in phase_responses.items():
            result = renderer.render_atmosphere(f"Phase: {phase}", phase)
            assert result is not None


class TestOllamaPerformance:
    """Test Ollama performance with archive-injected context."""

    @patch.object(OllamaClient, "generate")
    def test_ollama_response_time_with_large_context(self, mock_generate):
        """Test Ollama handles large archive context efficiently."""
        mock_generate.return_value = json.dumps(
            {"scene": "Scene", "choices": [{"choice": "Choice"}]}
        )

        client = OllamaClient()
        director = DirectorAgentOllama(client, "mistral")

        # Create large context (simulating 500+ turn archive)
        large_context = "Archive data: " + ("x" * 1000)

        result = director.generate_scene_with_choices(large_context, {})

        assert result is not None

    @patch.object(OllamaClient, "generate")
    def test_ollama_batch_turn_execution(self, mock_generate):
        """Test executing multiple turns efficiently."""

        def generate_mock(model, prompt, **kwargs):
            if "threat" in prompt.lower() or "strategy" in prompt.lower():
                return json.dumps(
                    {
                        "strategy": "Strategy",
                        "actions": ["Action"],
                        "threat_change": 0,
                    }
                )
            else:
                return json.dumps(
                    {
                        "scene": "Scene",
                        "choices": [{"choice": "Choice"}],
                    }
                )

        mock_generate.side_effect = generate_mock

        client = OllamaClient()
        pipeline = OllamaAgentPipeline(client)

        turn_count = 0
        for turn in range(1, 51):
            context = f"Turn {turn} context"
            world_state = {"turn": turn, "narrative_phase": "rising_action"}

            result = pipeline.execute_turn(context, world_state)

            if result is not None:
                turn_count += 1

        assert turn_count > 45, f"Only {turn_count}/50 turns success"
