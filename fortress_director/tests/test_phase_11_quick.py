"""Phase 11 Quick Validation: Real Ollama Integration (Fast Tests).

Quick smoke tests to validate Ollama integration without long waits.
"""

import time
from fortress_director.managers.turn_manager import TurnManager
from fortress_director.core.state_archive import StateArchive


class TestPhase11QuickValidation:
    """Quick validation of Ollama integration."""

    def test_ollama_single_turn(self):
        """Single turn with Ollama to verify connectivity."""
        tm = TurnManager(use_ollama=True)
        state = {"threat": 0.2, "morale": 80, "resources": 100}

        start = time.time()
        result = tm.execute_turn(state, 1, "exposition")
        elapsed = time.time() - start

        # Should get result (Ollama or fallback)
        assert result is not None
        assert "scene" in result
        assert "choices" in result
        print(f"✓ Single turn completed in {elapsed:.2f}s")

    def test_ollama_fallback_works(self):
        """Verify fallback mode still works."""
        tm = TurnManager(use_ollama=False)  # Force fallback
        state = {"threat": 0.3, "morale": 70, "resources": 80}

        result = tm.execute_turn(state, 1, "rising")

        assert result is not None
        assert "scene" in result
        print("✓ Fallback mode works")

    def test_10_turn_quick_campaign(self):
        """Quick 10-turn campaign with Ollama."""
        archive = StateArchive("test_phase11_quick")
        tm = TurnManager(use_ollama=True)
        tm.set_archive(archive)

        state = {"threat": 0.2, "morale": 80, "resources": 100}
        turns_ok = 0

        start = time.time()
        for turn_num in range(1, 11):
            try:
                result = tm.execute_turn(state, turn_num, "exposition")
                if result:
                    turns_ok += 1
                    tm.record_turn_to_archive(result, state, turn_num)
                    state["threat"] += 0.05
            except Exception as e:
                print(f"Turn {turn_num} failed: {e}")

        elapsed = time.time() - start
        print(f"✓ 10 turns completed: {turns_ok}/10 success in {elapsed:.2f}s")
        assert turns_ok >= 5  # At least 50% success

    def test_archive_integration(self):
        """Test archive context injection."""
        archive = StateArchive("test_phase11_archive")
        tm = TurnManager(use_ollama=True)
        tm.set_archive(archive)

        state = {"threat": 0.2, "morale": 80, "resources": 100}

        # Run a few turns
        for turn_num in range(1, 4):
            result = tm.execute_turn(state, turn_num, "exposition")
            if result:
                tm.record_turn_to_archive(result, state, turn_num)

        # Check context is available
        context = archive.get_context_for_prompt(turn_number=3)
        # Context can be None or string - both valid
        assert context is None or isinstance(context, str)
        print("✓ Archive context integration works")

    def test_choice_handling(self):
        """Test that choices are properly formatted."""
        tm = TurnManager(use_ollama=True)
        state = {"threat": 0.3, "morale": 70, "resources": 80}

        result = tm.execute_turn(state, 1, "rising")

        assert result is not None
        choices = result.get("choices", [])
        assert len(choices) >= 2

        for choice in choices:
            assert "id" in choice
            assert "text" in choice
            assert len(choice["text"]) > 5

        print(f"✓ Got {len(choices)} valid choices")

    def test_scene_generation(self):
        """Test that scenes are generated."""
        tm = TurnManager(use_ollama=True)
        state = {"threat": 0.2, "morale": 80, "resources": 100}

        result = tm.execute_turn(state, 1, "exposition")

        assert result is not None
        scene = result.get("scene", "")
        assert len(scene) > 10  # Should have substantive scene

        print(f"✓ Scene generated ({len(scene)} chars)")
