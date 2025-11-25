from fortress_director.core.threat_model import ThreatSnapshot
from fortress_director.narrative.event_graph import EventNode
from fortress_director.pipeline.endgame_detector import EndgameDetector


def _snapshot(phase: str):
    return ThreatSnapshot(
        base_threat=25,
        escalation=10.0,
        morale=20,
        resources=18,
        recent_hostility=6,
        turn=8,
        threat_score=75.0,
        phase=phase,
    )


def test_detector_reports_no_trigger_outside_collapse():
    detector = EndgameDetector()
    payload = detector.check({"metrics": {"morale": 60, "resources": 50}}, _snapshot("peak"))
    assert payload["final_trigger"] is False
    assert payload["reason"] is None
    assert payload["recommended_path"] == "strategic"


def test_detector_flags_low_morale_in_collapse():
    detector = EndgameDetector()
    state = {"metrics": {"morale": 10, "resources": 40}}
    payload = detector.check(state, _snapshot("collapse"))
    assert payload == {
        "final_trigger": True,
        "reason": "low_morale",
        "recommended_path": "desperate",
    }


def test_detector_uses_enemy_markers_when_resources_hold():
    detector = EndgameDetector(enemy_marker_threshold=2)
    state = {
        "metrics": {"morale": 40, "resources": 50},
        "map_event_markers": [
            {"entity_type": "enemy_probe"},
            {"entity_type": "enemy_breach", "hostile": True},
        ],
    }
    payload = detector.check(state, _snapshot("collapse"))
    assert payload["final_trigger"] is True
    assert payload["reason"] == "enemy_markers"
    assert payload["recommended_path"] == "heroic"


def test_detector_forces_final_when_event_node_is_final():
    detector = EndgameDetector()
    node = EventNode(
        id="node_final",
        description="Final encounter",
        tags=["collapse"],
        is_final=True,
    )
    payload = detector.check({}, _snapshot("peak"), event_node=node)
    assert payload["final_trigger"] is True
    assert payload["reason"] == "Reached final graph node: node_final"
    assert payload["recommended_path"] == "desperate"
