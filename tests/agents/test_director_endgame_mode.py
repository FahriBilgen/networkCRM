from fortress_director.agents.director_agent import DirectorAgent
from fortress_director.core.threat_model import ThreatSnapshot


def _collapse_snapshot() -> ThreatSnapshot:
    return ThreatSnapshot(
        base_threat=35,
        escalation=25.0,
        morale=18,
        resources=12,
        recent_hostility=7,
        turn=9,
        threat_score=78.0,
        phase="collapse",
    )


def test_director_enforces_endgame_options() -> None:
    agent = DirectorAgent(use_llm=False)
    projected_state = {"turn": 9, "world": {}, "metrics": {}}
    directive = {
        "final_trigger": True,
        "reason": "enemy_markers",
        "recommended_path": "desperate",
    }
    payload = agent.generate_intent(
        projected_state,
        threat_snapshot=_collapse_snapshot(),
        event_seed="final_breach",
        endgame_directive=directive,
    )
    scene_intent = payload["scene_intent"]
    assert scene_intent["risk_budget"] == 3
    assert scene_intent["final_directive"]["final_trigger"] is True
    options = payload["player_options"]
    assert len(options) == 2
    option_ids = {opt["id"] for opt in options}
    assert "heroic_choice" in option_ids
    assert "desperate_fallback" in option_ids
