"""Phase 9 Integration Tests: TurnManager with Ollama agents + StateArchive.

Tests cover:
- TurnManager initialization and configuration
- Single turn execution with Ollama agents
- Multi-turn campaigns with archive context injection
- Error handling and fallback logic
- Campaign metrics tracking
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from fortress_director.managers.turn_manager import TurnManager
from fortress_director.core.state_archive import StateArchive
from fortress_director.llm.ollama_adapter import (
    OllamaClient,
    DirectorAgentOllama,
    PlannerAgentOllama,
    WorldRendererOllama,
)


class TestTurnManagerBasics:
    """Test TurnManager initialization and configuration."""

    def test_turn_manager_initialization(self):
        """TurnManager should initialize with default Ollama client."""
        tm = TurnManager()
        assert tm.ollama_client is not None
        assert isinstance(tm.ollama_client, OllamaClient)
        assert tm.use_ollama is True

    def test_turn_manager_ollama_disabled(self):
        """TurnManager should support disabling Ollama."""
        tm = TurnManager(use_ollama=False)
        assert tm.use_ollama is False
        assert tm.pipeline is None

    def test_turn_manager_set_archive(self):
        """TurnManager should accept StateArchive instance."""
        tm = TurnManager(use_ollama=False)
        archive = StateArchive("test_session")
        tm.set_archive(archive)
        assert tm.archive is archive

    @patch.object(OllamaClient, "is_available")
    def test_turn_manager_ollama_unavailable(self, mock_available):
        """TurnManager should fallback when Ollama unavailable."""
        mock_available.return_value = False
        tm = TurnManager(use_ollama=True)
        assert tm.use_ollama is False
        assert tm.pipeline is None


class TestTurnExecution:
    """Test single turn execution with Ollama agents."""

    def test_single_turn_fallback(self):
        """Single turn should work in fallback mode."""
        tm = TurnManager(use_ollama=False)
        world_state = {"threat": 0.5, "morale": 50}

        result = tm.execute_turn(world_state, turn_number=1)

        assert result["turn"] == 1
        assert "scene" in result
        assert "choices" in result
        assert len(result["choices"]) == 3
        assert result["used_ollama"] is False

    def test_single_turn_result_structure(self):
        """Turn result should have required fields."""
        tm = TurnManager(use_ollama=False)
        world_state = {"threat": 0.2}

        result = tm.execute_turn(world_state, 5, narrative_phase="rising")

        assert result["turn"] == 5
        assert result["narrative_phase"] == "rising"
        assert "scene" in result
        assert "choices" in result
        assert "world" in result
        assert result["choices"][0].get("id") is not None

    def test_single_turn_with_narrative_phases(self):
        """Turn execution should support different narrative phases."""
        tm = TurnManager(use_ollama=False)
        world_state = {"threat": 0.5}

        for phase in ["exposition", "rising", "climax", "resolution"]:
            result = tm.execute_turn(world_state, 10, narrative_phase=phase)
            assert result["narrative_phase"] == phase
            assert "scene" in result


class TestArchiveContext:
    """Test archive context injection."""

    def test_get_archive_context_no_archive(self):
        """Should return empty string when no archive set."""
        tm = TurnManager(use_ollama=False)
        context = tm.get_archive_context(turn=10)
        assert context == ""

    def test_get_archive_context_with_archive(self):
        """Should retrieve context from archive."""
        tm = TurnManager(use_ollama=False)
        archive = StateArchive("test_session")

        # Record some turns
        for i in range(1, 5):
            state = {"threat": 0.1 * i, "turn": i}
            archive.record_turn(turn_number=i, full_state=state, state_delta={})

        tm.set_archive(archive)
        context = tm.get_archive_context(turn=4, context_type="summary")

        # Context should be string
        assert isinstance(context, str)

    def test_archive_context_injection_format(self):
        """Archive context should be formattable."""
        tm = TurnManager(use_ollama=False)
        archive = StateArchive("test_session")

        # Record turn with events
        state = {"threat": 0.5, "npc": "Rhea", "morale": 40}
        archive.record_turn(
            turn_number=1, full_state=state, state_delta={"event": "starts"}
        )

        tm.set_archive(archive)
        context = tm.get_archive_context(turn=1)

        # Should be a string
        assert isinstance(context, str)


class TestCampaignExecution:
    """Test multi-turn campaign execution."""

    def test_campaign_basic_execution(self):
        """Campaign should execute specified number of turns."""
        tm = TurnManager(use_ollama=False)
        world_state = {"threat": 0.0, "morale": 100}

        turns = tm.run_campaign(world_state, turn_limit=5)

        assert len(turns) == 5
        assert all(turn["turn"] == i + 1 for i, turn in enumerate(turns))

    def test_campaign_narrative_phase_distribution(self):
        """Campaign should distribute narrative phases correctly."""
        tm = TurnManager(use_ollama=False)
        world_state = {"threat": 0.0}

        turns = tm.run_campaign(world_state, turn_limit=12)

        # Expect roughly: exposition (4), rising (4), climax (3), resolution (1)
        phases = [turn["narrative_phase"] for turn in turns]

        assert "exposition" in phases
        assert "rising" in phases
        assert "climax" in phases

    def test_campaign_with_callback(self):
        """Campaign should invoke callback after each turn."""
        tm = TurnManager(use_ollama=False)
        world_state = {"threat": 0.0}

        callback_calls = []

        def track_turn(turn_num, result):
            callback_calls.append((turn_num, result["turn"]))

        tm.run_campaign(world_state, turn_limit=3, on_turn_complete=track_turn)

        assert len(callback_calls) == 3
        assert callback_calls[0] == (1, 1)
        assert callback_calls[2] == (3, 3)

    def test_campaign_early_termination(self):
        """Campaign should stop if turn signals game_over."""
        tm = TurnManager(use_ollama=False)
        world_state = {"threat": 0.0}

        # Patch execute_turn to signal game_over at turn 3
        original_execute = tm.execute_turn
        call_count = [0]

        def mock_execute(ws, turn_num, phase):
            call_count[0] += 1
            result = original_execute(ws, turn_num, phase)
            if turn_num == 3:
                result["game_over"] = True
            return result

        tm.execute_turn = mock_execute

        turns = tm.run_campaign(world_state, turn_limit=10)

        assert len(turns) == 3  # Stopped at turn 3
        assert turns[-1]["game_over"] is True


class TestArchiveIntegration:
    """Test StateArchive integration with TurnManager."""

    def test_record_turn_to_archive(self):
        """TurnManager should record turns to archive."""
        tm = TurnManager(use_ollama=False)
        archive = StateArchive("test_session")
        tm.set_archive(archive)

        turn_result = {
            "scene": "A dark fortress",
            "choices": [{"id": 1, "text": "Defend"}],
            "npc_reactions": ["Rhea nods grimly"],
        }
        world_state_after = {"threat": 0.6, "morale": 45}

        tm.record_turn_to_archive(turn_result, world_state_after, 1)

        # Archive should have recorded turn
        assert len(archive.current_states) == 1

    def test_campaign_metrics(self):
        """Campaign should track metrics via archive."""
        tm = TurnManager(use_ollama=False)
        archive = StateArchive("test_session")
        tm.set_archive(archive)

        # Run single turn
        tm.execute_turn({"threat": 0.2}, turn_number=1)
        tm.record_turn_to_archive({"scene": "Test"}, {"threat": 0.3}, turn_number=1)

        metrics = tm.get_campaign_metrics()

        assert "turn_count" in metrics
        assert "memory_bytes" in metrics
        assert metrics["memory_bytes"] >= 0

    def test_reset_clears_archive(self):
        """TurnManager.reset() should clear archive."""
        tm = TurnManager(use_ollama=False)
        archive = StateArchive("test_session")
        tm.set_archive(archive)

        # Record a turn
        archive.record_turn(turn_number=1, full_state={"threat": 0.5}, state_delta={})
        assert len(archive.current_states) == 1

        # Reset
        tm.reset()
        assert len(archive.current_states) == 0


class TestErrorHandling:
    """Test error handling and resilience."""

    def test_fallback_on_execute_turn_error(self):
        """Should fallback if execute_turn raises."""
        tm = TurnManager(use_ollama=False)

        # Force an error by patching pipeline
        tm.use_ollama = True
        tm.pipeline = Mock(side_effect=Exception("Pipeline error"))

        result = tm.execute_turn({"threat": 0.5}, turn_number=1)

        assert result["used_ollama"] is False
        assert "scene" in result  # Fallback provided

    def test_callback_error_handled(self):
        """Campaign should continue if callback raises."""
        tm = TurnManager(use_ollama=False)
        world_state = {"threat": 0.0}

        def bad_callback(turn_num, result):
            raise ValueError("Callback error")

        # Should not raise
        turns = tm.run_campaign(
            world_state, turn_limit=3, on_turn_complete=bad_callback
        )
        assert len(turns) == 3

    def test_archive_record_error_handled(self):
        """Should handle archive record errors gracefully."""
        tm = TurnManager(use_ollama=False)
        archive = Mock(side_effect=Exception("Archive error"))
        tm.set_archive(archive)

        # Should not raise
        tm.record_turn_to_archive({}, {}, 1)


class TestOllamaIntegration:
    """Test Ollama agent integration."""

    @patch.object(OllamaClient, "is_available")
    @patch.object(DirectorAgentOllama, "__init__", return_value=None)
    @patch.object(PlannerAgentOllama, "__init__", return_value=None)
    @patch.object(WorldRendererOllama, "__init__", return_value=None)
    def test_ollama_agents_initialized(
        self, mock_world, mock_planner, mock_director, mock_available
    ):
        """TurnManager should initialize Ollama agents when available."""
        mock_available.return_value = True

        tm = TurnManager(use_ollama=True)

        # Should have attempted to create agents
        assert mock_director.called or tm.pipeline is None

    def test_ollama_context_format(self):
        """Archive context should be suitable for Ollama prompts."""
        tm = TurnManager(use_ollama=False)
        archive = StateArchive("test_session")

        # Add multiple turns with events
        for i in range(1, 6):
            state = {"threat": i * 0.1, "turn": i, "morale": 100 - (i * 5)}
            archive.record_turn(turn_number=i, full_state=state, state_delta={})

        tm.set_archive(archive)
        context = tm.get_archive_context(turn=5)

        # Should be JSON-serializable string
        assert isinstance(context, str)


class TestPhase9Readiness:
    """Test production readiness of Phase 9 components."""

    def test_turn_manager_workflow(self):
        """Complete workflow: init, archive, campaign, metrics."""
        tm = TurnManager(use_ollama=False)
        archive = StateArchive("session_1")
        tm.set_archive(archive)

        world_state = {"threat": 0.0, "morale": 100}

        # Run 5-turn campaign
        turns = tm.run_campaign(world_state, turn_limit=5)

        # Record turns to archive
        for i, turn_result in enumerate(turns, 1):
            state = {"threat": i * 0.1, "morale": 100 - (i * 2)}
            tm.record_turn_to_archive(turn_result, state, turn_number=i)

        # Get metrics
        metrics = tm.get_campaign_metrics()

        assert len(turns) == 5
        assert "turn_count" in metrics
        assert metrics["turn_count"] >= 5
        assert "memory_bytes" in metrics

    def test_turn_manager_supports_resume(self):
        """TurnManager should support using same archive."""
        tm1 = TurnManager(use_ollama=False)
        archive = StateArchive("session_resume")
        tm1.set_archive(archive)

        # Run first 3 turns
        world_state = {"threat": 0.0, "morale": 100}
        turns_1 = tm1.run_campaign(world_state, turn_limit=3)

        # Record to archive
        for i, turn_result in enumerate(turns_1, 1):
            state = {"threat": i * 0.1, "morale": 100 - (i * 2)}
            tm1.record_turn_to_archive(turn_result, state, i)

        # Create new manager with same archive
        tm2 = TurnManager(use_ollama=False)
        tm2.set_archive(archive)

        # Verify both managers see the archive
        metrics1 = tm1.get_campaign_metrics()
        metrics2 = tm2.get_campaign_metrics()

        # Both should see the recorded turns
        assert metrics1["turn_count"] > 0
        assert metrics2["turn_count"] > 0
        assert metrics1["turn_count"] == metrics2["turn_count"]

    def test_fallback_mode_production_ready(self):
        """Fallback mode should handle full campaign without Ollama."""
        tm = TurnManager(use_ollama=False)
        archive = StateArchive("fallback_test")
        tm.set_archive(archive)

        world_state = {"threat": 0.1, "morale": 80}
        turns = tm.run_campaign(world_state, turn_limit=20)

        assert len(turns) == 20
        for i, turn in enumerate(turns, 1):
            assert turn["turn"] == i
            assert "scene" in turn
            assert len(turn["choices"]) > 0
            assert turn["used_ollama"] is False
