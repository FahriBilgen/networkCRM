from types import SimpleNamespace

from fortress_director.pipeline.endgame_detector import EndgameDetector
from fortress_director.narrative.demo_graph import DEMO_EVENT_GRAPH


def test_endgame_detector_final_node():
    detector = EndgameDetector()
    node = DEMO_EVENT_GRAPH.get_node("node_final")
    game_state = {"metrics": {}, "turn": 10}
    threat = SimpleNamespace(phase="calm")
    res = detector.check(game_state, threat, event_node=node)
    assert res["final_trigger"] is True
    assert "recommended_path" in res
