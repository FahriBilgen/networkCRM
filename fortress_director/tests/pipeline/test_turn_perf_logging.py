import json

from fortress_director.agents.director_agent import DirectorAgent
from fortress_director.agents.planner_agent import PlannerAgent
from fortress_director.agents.world_renderer_agent import WorldRendererAgent
from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import TurnManager
from fortress_director.themes.loader import BUILTIN_THEMES, load_theme_from_file


def test_turn_manager_perf_logging(tmp_path, monkeypatch) -> None:
    import fortress_director.pipeline.turn_manager as tm

    original_log = tm.TURN_PERF_LOG
    tm.TURN_PERF_LOG = tmp_path / "turn_perf.log"
    try:
        manager = TurnManager(
            director_agent=DirectorAgent(use_llm=False),
            planner_agent=PlannerAgent(use_llm=False),
            world_renderer_agent=WorldRendererAgent(use_llm=False),
        )
        game_state = GameState()
        theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
        manager.run_turn(game_state, theme=theme)
    finally:
        tm.TURN_PERF_LOG = original_log
    log_contents = (tmp_path / "turn_perf.log").read_text(encoding="utf-8").strip()
    assert log_contents
    entry = json.loads(log_contents.splitlines()[-1])
    assert "duration_ms" in entry
    assert entry["llm_calls"] >= 0
    assert "phase" in entry
