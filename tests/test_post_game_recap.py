from __future__ import annotations

from copy import deepcopy

from fortress_director.orchestrator.orchestrator import (
    DEFAULT_WORLD_STATE,
    Orchestrator,
)


def _state():
    data = deepcopy(DEFAULT_WORLD_STATE)
    data["turn"] = 5
    return data


def test_record_turn_recap_tracks_choice_and_safe_function() -> None:
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = _state()

    orchestrator._record_turn_recap(
        state,
        turn=5,
        player_choice={"id": "opt_a", "text": "Hold the wall", "action_type": "defend"},
        options=[
            {"id": "opt_a", "text": "Hold the wall", "action_type": "defend"},
            {"id": "opt_b", "text": "Parley", "action_type": "dialog"},
        ],
        safe_function_results=[
            {"name": "reinforce_structure", "metadata": {"source": "character:Rhea"}, "success": True}
        ],
        judge_verdict={"consistent": False, "penalty": "mild", "reason": "Lore break"},
    )

    history = state["_turn_history"]
    assert len(history) == 1
    entry = history[0]
    assert entry["choice"]["id"] == "opt_a"
    assert entry["safe_functions"][0]["name"] == "reinforce_structure"
    assert entry["judge"]["penalty"] == "mild"


def test_build_post_game_recap_summarizes_history() -> None:
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = _state()
    orchestrator._record_turn_recap(
        state,
        turn=4,
        player_choice={"id": "opt_c", "text": "Scout", "action_type": "explore"},
        options=[{"id": "opt_c", "text": "Scout", "action_type": "explore"}],
        safe_function_results=[],
        judge_verdict={"consistent": True, "penalty": "none"},
    )
    state["final_summary_cards"] = [
        {"ending": "victory", "title": "Citadel Holds", "description": "Win"}
    ]

    recap = orchestrator._build_post_game_recap(state)

    assert recap["turns_played"] == state["turn"]
    assert recap["choices"][0]["choice_id"] == "opt_c"
    assert recap["ending"] == "victory"
