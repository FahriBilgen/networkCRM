from __future__ import annotations

from fortress_director.agents.world_renderer_agent import WorldRendererAgent


def test_render_final_builds_three_paragraphs() -> None:
    agent = WorldRendererAgent(use_llm=False)
    final_context = {
        "final_path": {
            "id": "victory_defense",
            "title": "Victory Through Vigilance",
            "summary": "Defenders hold the walls.",
            "tone": "triumphant",
        },
        "world_context": {
            "event_history": [
                {"text": "Ordered the evacuation."},
                {"text": "Held the western wall."},
            ],
            "npc_outcomes": [{"id": "npc_1", "name": "Scout Ila", "fate": "alive"}],
            "structure_outcomes": [{"id": "inner_gate", "status": "stable", "integrity": 80}],
            "resource_summary": {"morale": 70, "resources": 55},
            "threat": {"phase": "peak", "score": 88},
        },
    }
    payload = agent.render_final(final_context)
    assert payload["title"] == "Victory Through Vigilance"
    assert len(payload["closing_paragraphs"]) == 3
    assert payload["npc_fates"]
    assert payload["structure_report"]
    assert payload["leadership_note"]
    assert payload["atmosphere"]["mood"] == "uplifted"
