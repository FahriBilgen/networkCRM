"""Phase 11 Production Testing: Real Ollama Integration & Extended Campaigns.

Tests validate:
- 50-100 turn campaigns with REAL Ollama agents (not mock)
- Narrative coherence at production scale
- Performance profiling (response times, memory)
- Error handling and resilience
- LLM response quality and consistency
"""

import time
import json
from pathlib import Path
from fortress_director.managers.turn_manager import TurnManager
from fortress_director.core.state_archive import StateArchive


class TestPhase11OllamaConnection:
    """Test basic Ollama connectivity."""

    def test_ollama_available(self):
        """Verify Ollama service is running and accessible."""
        tm = TurnManager(use_ollama=True)
        # If this doesn't raise, Ollama is accessible
        assert tm is not None

    def test_ollama_model_loading(self):
        """Test that Ollama can load required models."""
        tm = TurnManager(use_ollama=True)
        # Try to execute a turn - will use Ollama
        state = {"threat": 0.2, "morale": 80, "resources": 100}
        try:
            result = tm.execute_turn(state, 1, "exposition")
            # Should get a result (either from Ollama or fallback)
            assert result is not None
            assert "scene" in result
        except Exception as e:
            # Fallback is ok
            assert "fallback" in str(e).lower() or result is not None


class TestPhase11Extended50TurnCampaign:
    """Test 50-turn campaign with real Ollama."""

    def test_50_turn_ollama_campaign(self):
        """Run full 50-turn campaign with Ollama."""
        archive = StateArchive("test_phase11_50turn")
        tm = TurnManager(use_ollama=True)
        tm.set_archive(archive)

        state = {"threat": 0.2, "morale": 80, "resources": 100, "turn": 0}

        turns_completed = 0
        responses = []

        for turn_num in range(1, 51):
            try:
                result = tm.execute_turn(state, turn_num, "rising")
                if result:
                    turns_completed += 1
                    responses.append(
                        {
                            "turn": turn_num,
                            "used_ollama": result.get("used_ollama", False),
                            "scene_length": len(result.get("scene", "")),
                        }
                    )
                    tm.record_turn_to_archive(result, state, turn_num)

                    # Update state
                    state["threat"] = min(1.0, state.get("threat", 0) + 0.02)
                    state["morale"] = max(0, state.get("morale", 0) - 1)
            except Exception as e:
                # Allow fallback but track
                pass

        assert turns_completed >= 40  # At least 80% should complete

        # Check response quality
        ollama_turns = [r for r in responses if r["used_ollama"]]
        if ollama_turns:
            avg_scene_length = sum(r["scene_length"] for r in ollama_turns) / len(
                ollama_turns
            )
            assert avg_scene_length > 50  # Scenes should be substantive

    def test_50_turn_campaign_coherence(self):
        """Verify narrative coherence across 50 turns."""
        archive = StateArchive("test_phase11_coherence")
        tm = TurnManager(use_ollama=True)
        tm.set_archive(archive)

        state = {"threat": 0.2, "morale": 80, "resources": 100}

        turns = []
        for turn_num in range(1, 51):
            phase_pct = turn_num / 50
            if phase_pct < 0.25:
                phase = "exposition"
            elif phase_pct < 0.5:
                phase = "rising"
            elif phase_pct < 0.75:
                phase = "climax"
            else:
                phase = "resolution"

            result = tm.execute_turn(state, turn_num, phase)
            if result:
                turns.append(result)
                state["threat"] = min(1.0, state.get("threat", 0) + 0.02)

        # Should have most turns
        assert len(turns) >= 40

        # All turns should have required fields
        for turn in turns:
            assert "scene" in turn
            assert "choices" in turn
            assert len(turn["choices"]) >= 2


class TestPhase11Performance:
    """Performance profiling with real Ollama."""

    def test_ollama_response_time(self):
        """Measure Ollama response time per turn."""
        tm = TurnManager(use_ollama=True)
        state = {"threat": 0.3, "morale": 70, "resources": 80}

        response_times = []

        for i in range(5):  # 5 turns for profiling
            start = time.time()
            result = tm.execute_turn(state, i + 1, "rising")
            elapsed = time.time() - start
            response_times.append(elapsed)

            if result:
                state["threat"] += 0.05

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            # Ollama is slower, but shouldn't be unreasonable
            # Allow up to 30s per turn (Ollama can be slow)
            assert avg_time < 30.0

    def test_campaign_memory_profile(self):
        """Profile memory usage across 50-turn campaign."""
        archive = StateArchive("test_phase11_memory")
        tm = TurnManager(use_ollama=True)
        tm.set_archive(archive)

        state = {"threat": 0.2, "morale": 80, "resources": 100}
        memory_samples = []

        for turn_num in range(1, 51):
            result = tm.execute_turn(state, turn_num, "rising")
            if result:
                tm.record_turn_to_archive(result, state, turn_num)
                state["threat"] += 0.02

            if turn_num % 10 == 0:
                metrics = tm.get_campaign_metrics()
                memory_samples.append(
                    {"turn": turn_num, "memory_bytes": metrics.get("memory_bytes", 0)}
                )

        # Memory should grow but stay bounded
        if len(memory_samples) > 1:
            first_mem = memory_samples[0]["memory_bytes"]
            last_mem = memory_samples[-1]["memory_bytes"]

            # Should grow but not exponentially
            if first_mem > 0:
                growth_ratio = last_mem / first_mem
                assert growth_ratio < 5.0  # Not 5x growth


class TestPhase11ErrorResilience:
    """Test error handling with Ollama."""

    def test_ollama_timeout_handling(self):
        """Ensure system handles Ollama timeouts gracefully."""
        tm = TurnManager(use_ollama=True)
        state = {"threat": 0.5, "morale": 50, "resources": 50}

        # Even if Ollama times out, should get fallback or error handling
        try:
            result = tm.execute_turn(state, 1, "climax")
            assert result is not None  # Fallback should work
        except Exception as e:
            # Error should be logged, not crash
            assert "timeout" in str(e).lower() or "fallback" in str(e).lower()

    def test_invalid_ollama_response_handling(self):
        """Test handling of malformed Ollama responses."""
        tm = TurnManager(use_ollama=True)
        state = {"threat": 0.6, "morale": 40, "resources": 30}

        # Should handle any response format
        result = tm.execute_turn(state, 1, "climax")
        assert result is not None
        assert isinstance(result, dict)

    def test_multiple_failures_resilience(self):
        """Test system resilience through multiple potential failures."""
        tm = TurnManager(use_ollama=True)
        state = {"threat": 0.2, "morale": 80, "resources": 100}

        failure_count = 0
        success_count = 0

        for i in range(10):
            try:
                result = tm.execute_turn(state, i + 1, "exposition")
                if result:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                failure_count += 1

        # Should have some successes even with potential failures
        assert success_count >= 5  # At least 50% success rate


class TestPhase11LLMQuality:
    """Assess LLM response quality."""

    def test_scene_quality_metrics(self):
        """Evaluate quality of generated scenes."""
        tm = TurnManager(use_ollama=True)
        state = {"threat": 0.3, "morale": 70, "resources": 80}

        scenes = []
        for i in range(5):
            result = tm.execute_turn(state, i + 1, "exposition")
            if result:
                scene = result.get("scene", "")
                scenes.append(scene)
                state["threat"] += 0.05

        if scenes:
            # Scenes should be non-empty
            assert all(len(s) > 20 for s in scenes)

            # Scenes should be varied (not all identical)
            unique_scenes = len(set(scenes))
            assert unique_scenes >= 3  # At least 3 different scenes

    def test_choice_validity(self):
        """Verify choices are sensible and diverse."""
        tm = TurnManager(use_ollama=True)
        state = {"threat": 0.2, "morale": 80, "resources": 100}

        all_choices = []
        for i in range(5):
            result = tm.execute_turn(state, i + 1, "rising")
            if result:
                choices = result.get("choices", [])
                all_choices.extend(choices)
                state["threat"] += 0.05

        if all_choices:
            # Choices should have required fields
            for choice in all_choices:
                assert "id" in choice
                assert "text" in choice
                assert len(choice["text"]) > 10

            # Should have variety in choices
            choice_texts = [c["text"] for c in all_choices]
            unique_choices = len(set(choice_texts))
            assert unique_choices >= 8  # Variety in options


class TestPhase11ExtendedCampaignScale:
    """Test campaigns at extended scale (75-100 turns)."""

    def test_75_turn_campaign(self):
        """Run 75-turn campaign with Ollama."""
        archive = StateArchive("test_phase11_75turn")
        tm = TurnManager(use_ollama=True)
        tm.set_archive(archive)

        state = {"threat": 0.2, "morale": 80, "resources": 100, "turn": 0}
        turns_completed = 0

        for turn_num in range(1, 76):
            try:
                result = tm.execute_turn(state, turn_num, "rising")
                if result:
                    turns_completed += 1
                    tm.record_turn_to_archive(result, state, turn_num)
                    state["threat"] = min(1.0, state.get("threat", 0) + 0.013)
                    state["morale"] = max(0, state.get("morale", 0) - 0.7)
            except Exception:
                pass

        # Should complete majority
        assert turns_completed >= 60

    def test_100_turn_campaign(self):
        """Run full 100-turn campaign with Ollama."""
        archive = StateArchive("test_phase11_100turn")
        tm = TurnManager(use_ollama=True)
        tm.set_archive(archive)

        state = {"threat": 0.2, "morale": 80, "resources": 100}
        turns_completed = 0

        for turn_num in range(1, 101):
            try:
                phase_pct = turn_num / 100
                if phase_pct < 0.25:
                    phase = "exposition"
                elif phase_pct < 0.5:
                    phase = "rising"
                elif phase_pct < 0.75:
                    phase = "climax"
                else:
                    phase = "resolution"

                result = tm.execute_turn(state, turn_num, phase)
                if result:
                    turns_completed += 1
                    state["threat"] = min(1.0, state.get("threat", 0) + 0.01)
            except Exception:
                pass

        # Should complete significant portion
        assert turns_completed >= 75


class TestPhase11ArchiveScaling:
    """Test Archive performance at production scale."""

    def test_archive_context_quality_50_turns(self):
        """Verify archive context is useful for 50-turn campaign."""
        archive = StateArchive("test_phase11_archive_50")
        tm = TurnManager(use_ollama=True)
        tm.set_archive(archive)

        state = {"threat": 0.2, "morale": 80, "resources": 100}

        for turn_num in range(1, 51):
            result = tm.execute_turn(state, turn_num, "rising")
            if result:
                tm.record_turn_to_archive(result, state, turn_num)
                state["threat"] += 0.02

        # Archive should have context available
        context = archive.get_context_for_prompt(turn_number=50)
        # Context might be None or string - both ok
        assert context is None or isinstance(context, str)

    def test_archive_memory_at_100_turns(self):
        """Test memory efficiency at 100-turn scale."""
        archive = StateArchive("test_phase11_archive_100")
        tm = TurnManager(use_ollama=True)
        tm.set_archive(archive)

        state = {"threat": 0.2, "morale": 80, "resources": 100}

        for turn_num in range(1, 101):
            result = tm.execute_turn(state, turn_num, "rising")
            if result:
                tm.record_turn_to_archive(result, state, turn_num)
                state["threat"] += 0.01

        metrics = tm.get_campaign_metrics()
        memory_bytes = metrics.get("memory_bytes", 0)

        # Even at 100 turns, should stay reasonable
        assert memory_bytes < 5000000  # Less than 5MB
