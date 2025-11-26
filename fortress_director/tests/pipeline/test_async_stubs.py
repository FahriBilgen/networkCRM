import pytest

from fortress_director.pipeline.turn_manager import TurnManager


class DummyDirector:
    def __init__(self) -> None:
        self.calls = 0

    def generate_intent(self, *args, **kwargs):
        self.calls += 1
        return {"scene_intent": {"focus": "test"}}


class DummyPlanner:
    def __init__(self) -> None:
        self.calls = 0

    def plan_actions(self, *args, **kwargs):
        self.calls += 1
        return {"planned_actions": []}


class DummyRenderer:
    def __init__(self) -> None:
        self.calls = 0

    def render(self, *args, **kwargs):
        self.calls += 1
        return {"narrative_block": "ok", "npc_dialogues": [], "atmosphere": {}}


@pytest.mark.asyncio
async def test_async_wrappers_delegate_to_sync_methods() -> None:
    manager = TurnManager(
        director_agent=DummyDirector(),
        planner_agent=DummyPlanner(),
        world_renderer_agent=DummyRenderer(),
    )
    projected_state = {}
    await manager.run_director_async(
        projected_state,
        None,
        threat_snapshot=None,
        event_seed="seed",
        endgame_directive={},
        event_node=None,
    )
    await manager.run_planner_async(
        projected_state,
        {"focus": "test"},
        player_action_context=None,
        max_calls=1,
    )
    await manager.run_renderer_async(
        {},
        [],
        threat_phase="calm",
        event_seed=None,
        event_node=None,
        world_tick_delta=None,
    )
    assert manager.director_agent.calls == 1
    assert manager.planner_agent.calls == 1
    assert manager.world_renderer_agent.calls == 1
