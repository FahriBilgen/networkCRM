from fortress_director.agents.world_renderer_agent import WorldRendererAgent


def _world_state() -> dict:
    return {
        "turn": 5,
        "world": {"stability": 40, "resources": 30},
        "metrics": {"order": 45, "morale": 48, "resources": 30, "corruption": 15},
        "structures": {
            "gate": {
                "id": "gate",
                "kind": "gate",
                "x": 3,
                "y": 1,
                "integrity": 60,
                "max_integrity": 100,
                "on_fire": True,
            }
        },
        "stockpiles": {"food": 15},
    }


def _combat_action() -> list[dict]:
    return [
        {
            "function": "melee_engagement",
            "effects": {
                "combat": {
                    "outcome": {
                        "attackers_casualties": 2,
                        "defenders_casualties": 3,
                        "structure_damage": 4,
                    },
                    "structure": {"id": "gate"},
                }
            },
        }
    ]


def test_renderer_prompt_contains_simulation_blocks() -> None:
    agent = WorldRendererAgent(use_llm=False)
    prompt = agent._build_prompt(
        _world_state(),
        _combat_action(),
        world_tick_delta={"food_consumed": 4, "avg_fatigue": 72},
        combat_summary=[{"text": "Skirmish cost attackers 2, defenders 3."}],
    )
    assert "food_consumed" in prompt
    assert "Skirmish cost attackers 2" in prompt
    assert "Structures Actively On Fire" in prompt


def test_fallback_render_mentions_hunger_and_fatigue() -> None:
    agent = WorldRendererAgent(use_llm=False)
    world_tick_delta = {
        "food_consumed": 6,
        "avg_fatigue": 80,
        "events": ["Ash smothers the courtyard."],
    }
    result = agent.render(
        _world_state(),
        _combat_action(),
        world_tick_delta=world_tick_delta,
    )
    assert "Storerooms" in result["narrative_block"]
    visuals = result["atmosphere"]["visuals"].lower()
    assert "smoke" in visuals or "soot" in visuals or "storerooms" in visuals
