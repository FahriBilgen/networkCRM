from fortress_director.core.threat_model import ThreatModel


def _build_state(*, morale: int, resources: int, turn: int, history=None):
    return {
        "turn": turn,
        "metrics": {
            "morale": morale,
            "resources": resources,
            "threat": 20,
        },
        "safe_function_history": history or [],
    }


def test_threat_model_identifies_calm_phase():
    model = ThreatModel({"base_threat": 18})
    snapshot = model.compute(
        _build_state(morale=85, resources=70, turn=1, history=[]),
    )
    assert snapshot.phase == "calm"
    assert snapshot.threat_score < 20


def test_threat_model_identifies_rising_phase_with_combat_history():
    model = ThreatModel({"base_threat": 22})
    history = [
        {"name": "deploy_archers", "category": "combat"},
        {"name": "reinforce_wall", "category": "structure"},
    ]
    snapshot = model.compute(
        _build_state(morale=70, resources=55, turn=4, history=history),
    )
    assert snapshot.phase == "rising"
    assert snapshot.recent_hostility >= 3


def test_threat_model_hits_collapse_when_everything_drops():
    model = ThreatModel({"base_threat": 30})
    history = [
        {"name": "enemy_assault", "category": "combat"},
        {"name": "suppressive_fire", "category": "combat"},
        {"name": "apply_combat_pressure", "category": "combat"},
    ]
    snapshot = model.compute(
        _build_state(morale=20, resources=10, turn=12, history=history),
    )
    assert snapshot.phase == "collapse"
    assert snapshot.threat_score >= 65
