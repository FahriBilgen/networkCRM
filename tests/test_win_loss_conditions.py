"""Test for long game runs and win/loss conditions."""

import pytest
from fortress_director.rules.rules_engine import RulesEngine


class MockJudge:
    """Mock judge agent for testing."""

    def evaluate(self, variables):
        return {"consistent": True, "reason": "Mock response"}


@pytest.fixture
def rules_engine():
    """Create rules engine for testing."""
    judge = MockJudge()
    return RulesEngine(judge_agent=judge, tolerance=1)


def test_win_loss_conditions(rules_engine):
    """Test all win/loss conditions work correctly."""

    # Victory: survived 15+ turns with high morale and order
    state = {"metrics": {"morale": 65, "order": 75}}
    result = rules_engine.evaluate_win_loss(state, 16)
    assert result["status"] == "victory"
    assert result["reason"] == "survived_15_turns_high_morale"

    # Victory: perfect harmony
    state = {"metrics": {"morale": 85, "corruption": 3}}
    result = rules_engine.evaluate_win_loss(state, 5)
    assert result["status"] == "victory"
    assert result["reason"] == "perfect_harmony"

    # Defeat: morale crash
    state = {"metrics": {"morale": 5}}
    result = rules_engine.evaluate_win_loss(state, 5)
    assert result["status"] == "defeat"
    assert result["reason"] == "morale_crash"

    # Defeat: resources depleted
    state = {"metrics": {"resources": 3}}
    result = rules_engine.evaluate_win_loss(state, 5)
    assert result["status"] == "defeat"
    assert result["reason"] == "resources_depleted"

    # Defeat: chaos overwhelms
    state = {"metrics": {"order": 15}}
    result = rules_engine.evaluate_win_loss(state, 5)
    assert result["status"] == "defeat"
    assert result["reason"] == "chaos_overwhelms"

    # Defeat: system glitch
    state = {"metrics": {"glitch": 85}}
    result = rules_engine.evaluate_win_loss(state, 5)
    assert result["status"] == "defeat"
    assert result["reason"] == "system_glitch"

    # Defeat: turn limit exceeded
    state = {"metrics": {"morale": 50}}
    result = rules_engine.evaluate_win_loss(state, 21)
    assert result["status"] == "defeat"
    assert result["reason"] == "turn_limit_exceeded"

    # Defeat: major events overwhelm
    state = {"metrics": {"morale": 25, "major_events_triggered": 4}}
    result = rules_engine.evaluate_win_loss(state, 5)
    assert result["status"] == "defeat"
    assert result["reason"] == "major_events_overwhelm"


def test_game_progression_simulation(rules_engine):
    """Simulate a game that eventually leads to victory or defeat."""

    # Start with neutral state
    base_state = {
        "metrics": {
            "morale": 50,
            "resources": 40,
            "order": 50,
            "corruption": 10,
            "glitch": 12,
            "major_events_triggered": 0,
        }
    }

    # Simulate 20 turns of gradual decline
    for turn in range(1, 21):
        state = base_state.copy()
        # Simulate gradual resource depletion (slower)
        state["metrics"]["resources"] = max(10, 40 - turn * 1)
        # Simulate increasing glitch (slower)
        state["metrics"]["glitch"] = min(100, 12 + turn * 2)

        result = rules_engine.evaluate_win_loss(state, turn)

        if turn < 20:
            assert result["status"] == "ongoing"
        else:
            # At turn 20, should be defeat due to turn limit
            assert result["status"] == "defeat"
            assert result["reason"] == "turn_limit_exceeded"


def test_early_victory_conditions(rules_engine):
    """Test that victory can be achieved before turn limit."""

    # Perfect harmony victory
    state = {"metrics": {"morale": 85, "corruption": 3}}
    result = rules_engine.evaluate_win_loss(state, 3)
    assert result["status"] == "victory"
    assert result["reason"] == "perfect_harmony"

    # Survival victory
    state = {"metrics": {"morale": 65, "order": 75}}
    result = rules_engine.evaluate_win_loss(state, 16)
    assert result["status"] == "victory"
    assert result["reason"] == "survived_15_turns_high_morale"
