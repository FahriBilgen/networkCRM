"""Tests for LLM fallback templates."""

import pytest

from fortress_director.llm.fallback_templates import (
    fallback_director_intent,
    fallback_planner_actions,
    fallback_renderer_narrative,
    should_trigger_fallback,
)


class TestFallbackDirectorIntent:
    """Test fallback director intent generation."""

    def test_fallback_intent_returns_dict(self):
        """Fallback intent should return a valid dict."""
        result = fallback_director_intent()
        assert isinstance(result, dict)
        assert "scene_intent" in result
        assert "fallback_triggered" in result

    def test_fallback_intent_has_required_fields(self):
        """Fallback intent should have scene_intent structure."""
        result = fallback_director_intent()
        scene = result["scene_intent"]
        assert "atmosphere" in scene
        assert "npc_focus" in scene
        assert "player_agency" in scene

    def test_fallback_intent_marked_as_fallback(self):
        """Fallback intent should be marked as fallback."""
        result = fallback_director_intent()
        assert result["fallback_triggered"] is True


class TestFallbackPlannerActions:
    """Test fallback planner actions generation."""

    def test_fallback_actions_returns_dict(self):
        """Fallback actions should return a valid dict."""
        projected_state = {"turn": 1, "metrics": {}}
        result = fallback_planner_actions(projected_state)
        assert isinstance(result, dict)
        assert "planned_actions" in result

    def test_fallback_actions_returns_list(self):
        """Fallback actions should contain a list of actions."""
        projected_state = {"turn": 1}
        result = fallback_planner_actions(projected_state)
        assert isinstance(result["planned_actions"], list)
        assert len(result["planned_actions"]) > 0

    def test_fallback_actions_have_valid_structure(self):
        """Each fallback action should have required fields."""
        projected_state = {"turn": 1}
        result = fallback_planner_actions(projected_state)
        for action in result["planned_actions"]:
            assert "function" in action
            assert "args" in action
            assert "explanation" in action

    def test_fallback_actions_marked_as_fallback(self):
        """Fallback actions should be marked as fallback."""
        projected_state = {"turn": 1}
        result = fallback_planner_actions(projected_state)
        assert result["fallback_triggered"] is True


class TestFallbackRendererNarrative:
    """Test fallback narrative generation."""

    def test_fallback_narrative_returns_dict(self):
        """Fallback narrative should return a valid dict."""
        world_state = {"metrics": {}}
        result = fallback_renderer_narrative(world_state)
        assert isinstance(result, dict)
        assert "narrative" in result
        assert "atmosphere" in result

    def test_fallback_narrative_is_string(self):
        """Fallback narrative should be a non-empty string."""
        world_state = {"metrics": {}}
        result = fallback_renderer_narrative(world_state)
        assert isinstance(result["narrative"], str)
        assert len(result["narrative"]) > 0

    def test_fallback_narrative_high_threat(self):
        """Fallback narrative should reflect high threat."""
        world_state = {"metrics": {"threat": 80, "morale": 50}}
        result = fallback_renderer_narrative(world_state)
        narrative = result["narrative"].lower()
        # Should mention threat/siege/pressure
        threat_keywords = ["siege", "enemy", "pressure", "relent"]
        assert any(word in narrative for word in threat_keywords)

    def test_fallback_narrative_low_morale(self):
        """Fallback narrative should reflect low morale."""
        world_state = {"metrics": {"threat": 30, "morale": 10}}
        result = fallback_renderer_narrative(world_state)
        narrative = result["narrative"].lower()
        # Should mention despair/hope/dire
        morale_kw = ["despair", "hope", "dire", "fades"]
        assert any(word in narrative for word in morale_kw)

    def test_fallback_narrative_normal_state(self):
        """Fallback narrative should reflect normal state."""
        world_state = {"metrics": {"threat": 50, "morale": 50}}
        result = fallback_renderer_narrative(world_state)
        narrative = result["narrative"].lower()
        # Should be neutral/holding
        normal_kw = ["holds", "battered", "assess"]
        assert any(word in narrative for word in normal_kw)

    def test_fallback_narrative_has_atmosphere(self):
        """Fallback narrative should include atmosphere."""
        world_state = {"metrics": {}}
        result = fallback_renderer_narrative(world_state)
        assert "atmosphere" in result
        assert "visual_tone" in result["atmosphere"]
        assert "emotional_weight" in result["atmosphere"]

    def test_fallback_narrative_marked_as_fallback(self):
        """Fallback narrative should be marked as fallback."""
        world_state = {"metrics": {}}
        result = fallback_renderer_narrative(world_state)
        assert result["fallback_triggered"] is True


class TestFallbackTriggerLogic:
    """Test fallback trigger decision logic."""

    def test_should_trigger_fallback_within_threshold(self):
        """Fallback should not trigger if within time threshold."""
        # Assume 30s per turn, threshold at 29s
        assert not should_trigger_fallback(20.0, timeout_threshold=29.0)
        assert not should_trigger_fallback(28.5, timeout_threshold=29.0)

    def test_should_trigger_fallback_exceeds_threshold(self):
        """Fallback should trigger if exceeding time threshold."""
        assert should_trigger_fallback(30.0, timeout_threshold=29.0)
        assert should_trigger_fallback(35.0, timeout_threshold=29.0)

    def test_should_trigger_fallback_edge_case(self):
        """Fallback trigger at exact threshold boundary."""
        assert not should_trigger_fallback(29.0, timeout_threshold=29.0)
        assert should_trigger_fallback(29.1, timeout_threshold=29.0)

    def test_should_trigger_fallback_default_threshold(self):
        """Fallback should use 29s default threshold."""
        # Default threshold is 29s
        assert not should_trigger_fallback(28.5)
        assert should_trigger_fallback(29.5)


class TestFallbackIntegration:
    """Integration tests for fallback system."""

    def test_all_fallbacks_return_valid_structures(self):
        """All fallback functions should return valid response structures."""
        world_state = {"metrics": {"threat": 50, "morale": 50, "turn": 1}}
        projected_state = world_state

        director_result = fallback_director_intent()
        planner_result = fallback_planner_actions(projected_state)
        renderer_result = fallback_renderer_narrative(world_state)

        assert director_result["fallback_triggered"]
        assert planner_result["fallback_triggered"]
        assert renderer_result["fallback_triggered"]

    def test_fallback_chain_produces_valid_turn_result(self):
        """Fallback results should be compatible with turn flow."""
        world_state = {
            "metrics": {"threat": 50, "morale": 50},
            "turn": 1,
        }

        # Get all fallback outputs
        director = fallback_director_intent()
        planner = fallback_planner_actions(world_state)
        renderer = fallback_renderer_narrative(world_state)

        # Verify they can be combined into a valid result
        assert director["scene_intent"]
        assert planner["planned_actions"]
        assert renderer["narrative"]
        assert renderer["atmosphere"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
