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

judge = JudgeAgent()
engine = RulesEngine(judge_agent=judge)
scene = "A mysterious figure lingers at the gate."
state = {
    "turn": 10,
    "metrics": {"morale": 50},
    "memory_layers": [
        f"Turn 7: {scene}",
        f"Turn 8: {scene}",
        f"Turn 9: {scene}",
    ],
}

try:
    new_state = engine.process(
        state=copy.deepcopy(state),
        character_events=[make_basic_event(scene)],
        world_context="",
        scene=scene,
        player_choice={"id": "1", "text": "Approach", "action_type": "communication"},
        seed=42,
    )
    print('morale', new_state["metrics"].get("morale"))
    print('flags', new_state.get('flags'))
except Exception as exc:
    print('exception', exc)
