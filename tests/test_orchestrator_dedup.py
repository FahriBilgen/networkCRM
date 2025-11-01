from __future__ import annotations

from fortress_director.orchestrator.orchestrator import Orchestrator


def test_dedup_and_vary_options() -> None:
    """Test that _dedup_and_vary_options dedups by text and action_type."""
    orchestrator = Orchestrator()

    options = [
        {"text": "Talk to the guard", "action_type": "dialogue"},
        {
            "text": "Talk to the guard",
            "action_type": "dialogue",
        },  # Duplicate text and type
        {"text": "Explore the area", "action_type": "explore"},
        {"text": "Fight the enemy", "action_type": "fight"},
        {"text": "Fight the enemy", "action_type": "fight"},  # Duplicate type
    ]

    deduped = orchestrator._dedup_and_vary_options(options)

    # Should have 3 unique options (first of each pair kept, second varied)
    assert len(deduped) == 3

    # Check that texts are unique
    texts = [opt["text"].lower() for opt in deduped]
    assert len(set(texts)) == len(texts)

    # Check that action_types are unique
    action_types = [opt["action_type"] for opt in deduped]
    assert len(set(action_types)) == len(action_types)
