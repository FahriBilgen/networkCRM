from __future__ import annotations

import random

from fortress_director.orchestrator.orchestrator import Orchestrator


def test_dedup_and_vary_options() -> None:
    """Test that _dedup_and_vary_options dedups by text and action_type."""
    random.seed(1337)
    orchestrator = Orchestrator.__new__(Orchestrator)

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

    # Check that we kept variety across action types even if some repeat
    action_types = [opt["action_type"] for opt in deduped]
    assert len(set(action_types)) >= 2
