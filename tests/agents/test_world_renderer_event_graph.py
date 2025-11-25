from fortress_director.agents.world_renderer_agent import (
    WorldRendererAgent,
)
from fortress_director.narrative.demo_graph import DEMO_EVENT_GRAPH
from fortress_director.narrative.event_graph import EventNode


def test_world_renderer_includes_event_node():
    wr = WorldRendererAgent(use_llm=False)
    world_state = {
        "turn": 3,
        "world": {"stability": 60, "resources": 80},
        "metrics": {},
    }
    actions = []
    node = DEMO_EVENT_GRAPH.get_node("node_reinforcement")
    payload = wr.render(
        world_state,
        actions,
        threat_phase="rising",
        event_seed="seed-x",
        event_node=node,
    )
    assert "narrative_block" in payload
    assert node.description in payload["narrative_block"]
    assert "atmosphere" in payload and isinstance(payload["atmosphere"], dict)


def _world_state() -> dict[str, object]:
    return {
        "turn": 3,
        "world": {"stability": 50, "resources": 40},
        "metrics": {"order": 55},
    }


def test_renderer_injects_event_description_into_narrative() -> None:
    agent = WorldRendererAgent(use_llm=False)
    node = EventNode(
        id="node_battle",
        description="Walls shake as engines crash against the gate.",
        tags=["battle"],
    )
    payload = agent.render(
        _world_state(),
        executed_actions=[],
        threat_phase="peak",
        event_node=node,
    )
    assert "Walls shake" in payload["narrative_block"]
    assert "Smoke" in payload["atmosphere"]["visuals"]


def test_renderer_adjusts_atmosphere_for_hopeful_node() -> None:
    agent = WorldRendererAgent(use_llm=False)
    node = EventNode(
        id="node_morale",
        description="Sunlight breaks through as reinforcements arrive.",
        tags=["hope"],
    )
    payload = agent.render(
        _world_state(),
        executed_actions=[],
        threat_phase="rising",
        event_node=node,
    )
    assert "Sunlight" in payload["atmosphere"]["visuals"]
    assert payload["atmosphere"]["mood"] == "hopeful"
