from fortress_director.agents import DirectorAgent, PlannerAgent, WorldRendererAgent
from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import TurnManager
from fortress_director.themes.loader import BUILTIN_THEMES, load_theme_from_file


def _load_theme(theme_id: str):
    return load_theme_from_file(BUILTIN_THEMES[theme_id])


def test_turn_manager_uses_theme_specific_event_graphs() -> None:
    siege_theme = _load_theme("siege_default")
    orbital_theme = _load_theme("orbital_outpost")
    manager = TurnManager(
        director_agent=DirectorAgent(use_llm=False),
        planner_agent=PlannerAgent(use_llm=False),
        world_renderer_agent=WorldRendererAgent(use_llm=False),
    )
    siege_state = GameState.from_theme_config(siege_theme)
    orbital_state = GameState.from_theme_config(orbital_theme)

    siege_result = manager.run_turn(siege_state, theme=siege_theme)
    orbital_result = manager.run_turn(orbital_state, theme=orbital_theme)

    assert siege_result.event_node_id == "siege_intro"
    assert orbital_result.event_node_id == "uplink_init"
    assert siege_result.event_node_description != orbital_result.event_node_description
