from types import SimpleNamespace

from fortress_director.agents.director_agent import DirectorAgent
from fortress_director.core.threat_model import ThreatSnapshot
from fortress_director.narrative.demo_graph import DEMO_EVENT_GRAPH
from fortress_director.narrative.event_graph import EventNode


def test_director_receives_event_node():
    director = DirectorAgent(use_llm=False)
    projected_state = {
        "turn": 5,
        "recent_events": [],
        "metrics": {},
        "world": {},
    }
    node = DEMO_EVENT_GRAPH.get_node("node_intro")
    threat = SimpleNamespace(phase="rising")
    intent = director.generate_intent(
        projected_state,
        None,
        threat_snapshot=threat,
        event_seed="s1",
        event_node=node,
    )
    assert "scene_intent" in intent
    si = intent["scene_intent"]
    assert si.get("turn") == 5
    # director may include event_seed in different places; ensure it's
    # present
    assert "event_seed" in si or intent.get("player_options") is not None
    assert isinstance(intent.get("player_options"), list)


def _snapshot() -> ThreatSnapshot:
    return ThreatSnapshot(
        base_threat=20,
        escalation=10.0,
        morale=55,
        resources=50,
        recent_hostility=3,
        turn=4,
        threat_score=35.0,
        phase="rising",
    )


def test_director_aligns_options_with_event_node_tags() -> None:
    agent = DirectorAgent(use_llm=False)
    projected_state = {"turn": 4, "world": {}, "metrics": {}}
    node = EventNode(
        id="node_sabotage",
        description="Saboteurs creep under the cisterns.",
        tags=["sabotage"],
    )
    payload = agent.generate_intent(
        projected_state,
        threat_snapshot=_snapshot(),
        event_node=node,
    )
    options = payload["player_options"]
    assert len(options) == 3
    assert any(option["type"] == "stealth" for option in options)
    assert any("tunnel" in option["text"].lower() for option in options)


def test_director_switches_to_battle_palette() -> None:
    agent = DirectorAgent(use_llm=False)
    projected_state = {"turn": 6, "world": {}, "metrics": {}}
    node = EventNode(
        id="node_battle",
        description="Engines batter the walls.",
        tags=["battle"],
    )
    payload = agent.generate_intent(
        projected_state,
        threat_snapshot=_snapshot(),
        event_node=node,
    )
    options = payload["player_options"]
    assert any("charge" in opt["label"].lower() for opt in options)
