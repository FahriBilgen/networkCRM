def test_character_trust_clamp():
    from fortress_director.agents.character_agent import CharacterAgent

    agent = CharacterAgent()
    # Simulate an entry with an extreme trust_delta
    entry = {
        "name": "Rhea",
        "intent": "vigilance",
        "action": "stand_vigilantly",
        "speech": "I watch the gates.",
        "effects": {"trust_delta": 100},
    }

    normalized = agent._normalise_entries([entry])
    assert isinstance(normalized, list) and normalized
    eff = normalized[0].get("effects", {})
    # trust_delta must have been clamped to 1
    assert eff.get("trust_delta") == 1
