from fortress_director.agents.director_agent import DirectorAgent
from fortress_director.core.threat_model import ThreatSnapshot


def _snapshot(phase: str, *, score: float = 35.0) -> ThreatSnapshot:
    return ThreatSnapshot(
        base_threat=20,
        escalation=10.0,
        morale=60,
        resources=55,
        recent_hostility=3,
        turn=5,
        threat_score=score,
        phase=phase,
    )


def test_director_focus_tracks_threat_phase() -> None:
    agent = DirectorAgent(use_llm=False)
    projected_state = {"turn": 5, "world": {}, "metrics": {}}
    payload = agent.generate_intent(
        projected_state,
        threat_snapshot=_snapshot("peak", score=58.0),
        event_seed="enemy_assault",
    )
    scene_intent = payload["scene_intent"]
    assert scene_intent["focus"] == "escalate"
    assert scene_intent["threat_phase"] == "peak"
    assert "enemy_assault" in scene_intent["notes"]
    option_types = {opt["type"] for opt in payload["player_options"]}
    assert "offense" in option_types


def test_director_shifts_to_exploration_in_calm_phase() -> None:
    agent = DirectorAgent(use_llm=False)
    projected_state = {"turn": 3, "world": {}, "metrics": {}}
    payload = agent.generate_intent(
        projected_state,
        threat_snapshot=_snapshot("calm", score=12.0),
        event_seed="supply_drop",
    )
    assert payload["scene_intent"]["focus"] == "explore"
    assert payload["scene_intent"]["threat_phase"] == "calm"
    assert any(opt["type"] == "recon" for opt in payload["player_options"])
