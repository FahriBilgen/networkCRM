from fortress_director.core.threat_model import ThreatSnapshot
from fortress_director.pipeline.event_curve import EventCurve


def _snapshot(phase: str, *, score: float = 15, turn: int = 1, hostility: int = 0):
    return ThreatSnapshot(
        base_threat=20,
        escalation=5.0,
        morale=70,
        resources=60,
        recent_hostility=hostility,
        turn=turn,
        threat_score=score,
        phase=phase,
    )


def test_event_curve_returns_calm_theme():
    curve = EventCurve()
    event = curve.next_event(_snapshot("calm", score=10), {"turn": 1, "metrics": {}})
    assert event in {"minor_scouting", "supply_drop", "weather_shift"}


def test_event_curve_prefers_collapse_events():
    curve = EventCurve()
    state = {
        "turn": 10,
        "metrics": {"morale": 15, "resources": 12},
        "map_event_markers": [{"entity_type": "enemy_probe"}, {"entity_type": "enemy_breach"}],
    }
    event = curve.next_event(
        _snapshot("collapse", score=80, turn=10, hostility=6),
        state,
    )
    assert event in {"final_breach", "last_reserve", "evacuation_crisis"}


def test_event_curve_is_deterministic_for_same_inputs():
    curve = EventCurve()
    snapshot = _snapshot("rising", score=32, turn=5, hostility=2)
    state = {"turn": 5, "metrics": {"morale": 50, "resources": 40}}
    assert curve.next_event(snapshot, state) == curve.next_event(snapshot, state)
