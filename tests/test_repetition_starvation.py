import copy

from fortress_director.agents.judge_agent import JudgeAgent
from fortress_director.rules.rules_engine import RulesEngine


def make_basic_event(speech: str):
    return {
        "name": "Rhea",
        "intent": "vigilance",
        "action": "stand_vigilantly",
        "speech": speech,
        "effects": {},
    }


def test_repetition_triggers_judge_penalty():
    judge = JudgeAgent()
    engine = RulesEngine(judge_agent=judge)

    scene = "A mysterious figure lingers at the gate."
    # Create state with the scene present 3 times in memory_layers
    state = {
        "turn": 10,
        "metrics": {"morale": 50},
        "memory_layers": [
            f"Turn 7: {scene}",
            f"Turn 8: {scene}",
            f"Turn 9: {scene}",
        ],
    }

    events = [make_basic_event(scene)]
    new_state = engine.process(
        state=copy.deepcopy(state),
        character_events=events,
        world_context="",
        scene=scene,
        player_choice={"id": "1", "text": "Approach", "action_type": "communication"},
        seed=42,
    )

    # Judge repetition logic should have applied at least a -1 morale penalty
    assert "metrics" in new_state
    assert new_state["metrics"].get("morale", 0) <= 49


def test_major_event_starvation_forces_flag():
    judge = JudgeAgent()
    engine = RulesEngine(judge_agent=judge)

    scene = "A quiet night watch."
    # Setup state where last major event was many turns ago
    state = {
        "turn": 20,
        "metrics": {"morale": 40, "major_event_last_turn": 5},
        "memory_layers": [],
        "flags": [],
    }

    events = [make_basic_event(scene)]
    new_state = engine.process(
        state=copy.deepcopy(state),
        character_events=events,
        world_context="",
        scene=scene,
        player_choice={"id": "1", "text": "Observe", "action_type": "observation"},
        seed=42,
    )

    # After processing, the rules engine should add force_major_event flag and reduce morale by at least 1
    assert "flags" in new_state
    assert "force_major_event" in new_state.get("flags", [])
    assert new_state["metrics"].get("morale", 0) <= 39
