from __future__ import annotations

from typing import Iterable, List
from unittest.mock import Mock

import pytest

from fortress_director.core.state_store import GameState
from fortress_director.llm.runtime_mode import set_llm_enabled
from fortress_director.pipeline import function_executor
from fortress_director.pipeline.turn_manager import TurnManager
from fortress_director.themes.loader import BUILTIN_THEMES, load_theme_from_file

set_llm_enabled(False)


def _run_turns_with_sequences(action_sequences: Iterable[List[dict]]) -> List[int]:
    """Drive the turn manager with mocked agents and collect executed counts."""

    sequences = [list(seq) for seq in action_sequences]
    game_state = GameState()
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    director = Mock()
    director.generate_intent.side_effect = lambda *_args, **_kwargs: {
        "scene_intent": {"focus": "stabilize"},
        "player_options": [
            {"id": "option_1", "label": "Reinforce defenses"},
            {"id": "option_2", "label": "Scout the perimeter"},
            {"id": "option_3", "label": "Commit reserves"},
        ],
    }
    planner = Mock()
    planner.plan_actions.side_effect = (
        {"planned_actions": payload} for payload in sequences
    )
    renderer = Mock()
    renderer.render.side_effect = [
        {
            "narrative_block": f"Turn {idx} resolved.",
            "npc_dialogues": [],
            "atmosphere": {"mood": "tense"},
        }
        for idx in range(len(sequences))
    ]
    manager = TurnManager(
        director_agent=director,
        planner_agent=planner,
        world_renderer_agent=renderer,
        function_executor_module=function_executor,
    )
    executed_per_turn: List[int] = []
    for idx in range(len(sequences)):
        payload = manager.run_turn(
            game_state,
            player_choice={"id": f"choice_{idx}"},
            theme=theme,
        )
        executed_per_turn.append(len(payload.executed_actions))
    return executed_per_turn


def _assert_minimum_usage(executed_counts: Iterable[int], min_calls: int) -> None:
    for idx, count in enumerate(executed_counts, start=1):
        assert (
            count >= min_calls
        ), f"Turn {idx} executed {count} safe functions (min required: {min_calls})."


def test_function_usage_rate_meets_minimum_with_mock_planner() -> None:
    action_sequences = [
        [
            {
                "function": "reinforce_wall",
                "args": {"structure_id": "western_wall", "amount": 2},
            }
        ],
        [
            {
                "function": "allocate_food",
                "args": {"amount": 2, "target": "patrol"},
            },
            {
                "function": "send_on_patrol",
                "args": {"npc_id": "rhea", "duration": 1},
            },
        ],
        [
            {
                "function": "patch_wall_section",
                "args": {"section_id": "sally_port", "amount": 1},
            }
        ],
        [
            {
                "function": "spawn_event_marker",
                "args": {"marker_id": "skyfire_signal", "x": 3, "y": 2},
            },
            {"function": "set_flag", "args": {"flag": "skyfire_ready"}},
        ],
        [
            {
                "function": "reinforce_wall",
                "args": {"structure_id": "inner_gate", "amount": 1},
            }
        ],
    ]
    executed_counts = _run_turns_with_sequences(action_sequences)
    assert len(executed_counts) == 5
    _assert_minimum_usage(executed_counts, min_calls=1)
    assert all(count <= 2 for count in executed_counts)


def test_function_usage_rate_detects_zero_call_turn() -> None:
    action_sequences = [
        [
            {
                "function": "reinforce_wall",
                "args": {"structure_id": "western_wall", "amount": 1},
            }
        ],
        [],
        [
            {
                "function": "allocate_food",
                "args": {"amount": 1, "target": "workers"},
            }
        ],
        [{"function": "set_flag", "args": {"flag": "lockdown_order"}}],
        [
            {
                "function": "spawn_event_marker",
                "args": {"marker_id": "signal", "x": 1, "y": 1},
            }
        ],
    ]
    executed_counts = _run_turns_with_sequences(action_sequences)
    with pytest.raises(AssertionError, match="Turn 2 executed 0 safe functions"):
        _assert_minimum_usage(executed_counts, min_calls=1)
