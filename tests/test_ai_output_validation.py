"""AI Output Validation Tests for Fortress Director."""

import os
import pytest
from typing import Dict, Any, List
from fortress_director.orchestrator.orchestrator import Orchestrator
from fortress_director.agents.event_agent import EventAgent
from fortress_director.agents.world_agent import WorldAgent
from fortress_director.agents.character_agent import CharacterAgent
from fortress_director.agents.judge_agent import JudgeAgent
from fortress_director.utils.output_validator import validate_turn_output
from fortress_director.rules.rules_engine import RulesEngine
from pathlib import Path
from fortress_director.orchestrator.orchestrator import StateStore


class AIOutputValidator:
    """Advanced validation for AI-generated content."""

    def __init__(self):
        self.validation_results = []

    def validate_content_quality(
        self, content: str, content_type: str
    ) -> Dict[str, Any]:
        """Validate content quality based on type-specific criteria."""
        result = {
            "type": content_type,
            "length": len(content),
            "has_substance": False,
            "is_coherent": False,
            "score": 0.0,
        }

        if not content or len(content.strip()) < 10:
            return result

        result["has_substance"] = True

        if content_type == "scene":
            keywords = ["stand", "entrance", "wall", "battle", "mist", "air"]
            result["is_coherent"] = any(
                keyword in content.lower() for keyword in keywords
            )
        elif content_type == "speech":
            result["is_coherent"] = "." in content or "!" in content or "?" in content
        elif content_type == "atmosphere":
            result["is_coherent"] = len(content.split()) >= 3

        score = 0.0
        if result["has_substance"]:
            score += 0.4
        if result["is_coherent"]:
            score += 0.4
        if result["length"] > 50:
            score += 0.2

        result["score"] = min(score, 1.0)
        return result

    def validate_structural_consistency(
        self, outputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate consistency across multiple AI outputs."""
        if not outputs:
            return {"consistent": False, "reason": "No outputs to compare"}

        first_keys = set(outputs[0].keys()) if outputs else set()
        all_consistent = all(set(output.keys()) == first_keys for output in outputs)

        contents = []
        for output in outputs:
            content_parts = []
            for key, value in output.items():
                if isinstance(value, str):
                    content_parts.append(value)
                elif isinstance(value, list) and key == "options":
                    opts = [
                        opt.get("text", "") for opt in value if isinstance(opt, dict)
                    ]
                    content_parts.extend(opts)
            contents.append(" ".join(content_parts))

        unique_contents = set(contents)
        content_diversity = len(unique_contents) / len(contents) if contents else 0

        return {
            "consistent": all_consistent,
            "content_diversity": content_diversity,
            "structure_similarity": 1.0 if all_consistent else 0.0,
            "overall_score": (1.0 if all_consistent else 0.0)
            * min(content_diversity + 0.5, 1.0),
        }

    def validate_lore_consistency(
        self, content: str, lore_elements: List[str]
    ) -> float:
        """Check if content is consistent with established lore."""
        if not lore_elements:
            return 1.0

        content_lower = content.lower()
        matches = sum(
            1 for element in lore_elements if element.lower() in content_lower
        )
        return matches / len(lore_elements)


@pytest.fixture
def output_validator():
    """Provide AIOutputValidator instance."""
    return AIOutputValidator()


@pytest.fixture
def orchestrator(tmp_path: Path) -> Orchestrator:
    """Create orchestrator for testing."""
    orchestrator = Orchestrator.__new__(Orchestrator)
    from fortress_director.codeaware.function_registry import SafeFunctionRegistry
    from fortress_director.codeaware.function_validator import FunctionCallValidator
    from fortress_director.codeaware.rollback_system import RollbackSystem

    state_store = StateStore(tmp_path / "world_state.json")
    orchestrator.state_store = state_store
    orchestrator.event_agent = EventAgent()
    orchestrator.world_agent = WorldAgent()
    orchestrator.character_agent = CharacterAgent()
    orchestrator.judge_agent = JudgeAgent()
    rules_engine = RulesEngine(judge_agent=orchestrator.judge_agent)
    orchestrator.rules_engine = rules_engine
    orchestrator.function_registry = SafeFunctionRegistry()
    function_validator = FunctionCallValidator(
        orchestrator.function_registry, max_calls_per_function=5, max_total_calls=20
    )
    orchestrator.function_validator = function_validator
    rollback_system = RollbackSystem(
        snapshot_provider=state_store.snapshot,
        restore_callback=state_store.persist,
        max_checkpoints=3,
    )
    orchestrator.rollback_system = rollback_system
    runs_dir = tmp_path / "runs" / "latest_run"
    runs_dir.mkdir(parents=True, exist_ok=True)
    orchestrator.runs_dir = runs_dir
    orchestrator._register_default_safe_functions()

    return orchestrator


@pytest.mark.integration
@pytest.mark.validation
def test_event_agent_output_quality_real_ai(output_validator):
    """Test EventAgent output quality with real AI."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI validation test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    agent = EventAgent()
    test_input = {
        "WORLD_CONTEXT": (
            "Turn 1 | Day 1 | Time morning\n"
            "Location: entrance\n"
            "Player: Test Player\n"
            "Recent events: none"
        ),
        "day": 1,
        "time": "morning",
        "room": "entrance",
        "recent_events": "none",
        "world_constraint_from_prev_turn": {"atmosphere": "clear sky"},
        "recent_motifs": "none",
        "lore_continuity_weight": 0,
        "memory_layers": [],
    }

    result = agent.generate(test_input)

    assert isinstance(result, dict)
    assert "scene" in result
    assert "options" in result
    assert isinstance(result["options"], list)

    scene_quality = output_validator.validate_content_quality(result["scene"], "scene")
    assert scene_quality["score"] > 0.5

    for i, option in enumerate(result["options"]):
        assert isinstance(option, dict)
        assert "text" in option
        option_quality = output_validator.validate_content_quality(
            option["text"], "option"
        )
        assert option_quality["score"] > 0.3


@pytest.mark.integration
@pytest.mark.validation
def test_world_agent_output_quality_real_ai(output_validator):
    """Test WorldAgent output quality with real AI."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip("Skipping real AI validation test; set FORTRESS_USE_OLLAMA=1")

    agent = WorldAgent()
    test_input = {
        "WORLD_CONTEXT": (
            "Turn 1 | Day 1 | Time morning\n"
            "Location: entrance\n"
            "Player: Test Player"
        ),
        "room": "entrance",
    }

    result = agent.describe(test_input)

    assert isinstance(result, dict)
    assert "atmosphere" in result
    assert "sensory_details" in result

    atmosphere_quality = output_validator.validate_content_quality(
        result["atmosphere"], "atmosphere"
    )
    sensory_quality = output_validator.validate_content_quality(
        result["sensory_details"], "sensory"
    )

    assert atmosphere_quality["score"] > 0.4
    assert sensory_quality["score"] > 0.4


@pytest.mark.integration
@pytest.mark.validation
def test_character_agent_output_quality_real_ai(output_validator):
    """Test CharacterAgent output quality with real AI."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI validation test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    agent = CharacterAgent()
    test_input = {
        "WORLD_CONTEXT": "Turn 1 | Day 1 | Time morning\nLocation: entrance\nPlayer: Test Player",
        "scene_short": "A character stands at the entrance",
        "player_choice": "Approach the character",
        "atmosphere": "Clear morning sky",
        "sensory_details": "Fresh air and distant sounds",
        "char_brief": "Test character",
        "relationship_summary_from_state": "Neutral relationship",
        "player_inventory_brief": "Basic items",
    }

    result = agent.react(test_input)

    assert isinstance(result, list)
    assert len(result) > 0

    for i, reaction in enumerate(result):
        assert isinstance(reaction, dict)
        assert "name" in reaction
        assert "speech" in reaction

        speech_quality = output_validator.validate_content_quality(
            reaction["speech"], "speech"
        )
        assert speech_quality["score"] > 0.4


@pytest.mark.integration
@pytest.mark.validation
def test_judge_agent_output_quality_real_ai(output_validator):
    """Test JudgeAgent output quality with real AI."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI validation test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    agent = JudgeAgent()
    test_input = {
        "WORLD_CONTEXT": "Test world context",
        "content": '{"scene": "test scene", "player_choice": {"text": "test choice"}, "character_update": {"name": "TestNPC", "intent": "test", "action": "test action", "speech": "test speech"}}',
    }

    result = agent.evaluate(test_input)

    assert isinstance(result, dict)
    assert "consistent" in result
    assert "reason" in result

    reason_quality = output_validator.validate_content_quality(
        result["reason"], "reason"
    )
    assert reason_quality["score"] > 0.5


@pytest.mark.integration
@pytest.mark.validation
def test_ai_output_consistency_across_runs_real_ai(orchestrator, output_validator):
    """Test AI output consistency across multiple runs."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI consistency test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    outputs = []

    for i in range(3):
        result = orchestrator.run_turn(player_choice_id="1")

        turn_output = {
            "scene": result.get("scene", ""),
            "atmosphere": result.get("world", {}).get("atmosphere", ""),
            "character_speech": (
                result.get("character_reactions", [{}])[0].get("speech", "")
                if result.get("character_reactions")
                else ""
            ),
            "options": [
                opt.get("text", "")
                for opt in result.get("event", {}).get("options", [])
            ],
        }
        outputs.append(turn_output)

    consistency_result = output_validator.validate_structural_consistency(outputs)
    assert consistency_result["consistent"]
    assert consistency_result["overall_score"] > 0.6


@pytest.mark.integration
@pytest.mark.validation
def test_full_turn_output_validation_real_ai(orchestrator):
    """Test that full turn outputs pass structural validation."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI validation test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    result = orchestrator.run_turn(player_choice_id="1")

    validate_turn_output(result)

    assert len(result.get("scene", "")) > 20
    assert len(result.get("narrative", "")) > 10

    world = result.get("world", {})
    assert len(world.get("atmosphere", "")) > 5
    assert len(world.get("sensory_details", "")) > 5


@pytest.mark.integration
@pytest.mark.validation
def test_ai_lore_consistency_real_ai(output_validator):
    """Test AI consistency with established lore elements."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip("Skipping real AI lore test; set FORTRESS_USE_OLLAMA=1 to run")

    # Simple lore consistency test - check EventAgent output
    lore_elements = [
        "Shieldbearer",
        "entrance",
        "wall",
        "battlements",
        "Rhea",
        "Boris",
        "oil lamp",
        "patched shield",
    ]

    # Test EventAgent
    event_agent = EventAgent()
    test_input = {
        "WORLD_CONTEXT": "Turn 1 | Day 1 | Time morning\nLocation: entrance\nPlayer: Test Player\nRecent events: none",
        "day": 1,
        "time": "morning",
        "room": "entrance",
        "recent_events": "none",
        "world_constraint_from_prev_turn": {"atmosphere": "clear sky"},
        "recent_motifs": "none",
        "lore_continuity_weight": 0,
        "memory_layers": [],
    }

    event_result = event_agent.generate(test_input)
    scene = event_result.get("scene", "")

    # Check if at least some lore elements are present
    matches = sum(1 for element in lore_elements if element.lower() in scene.lower())
    consistency_score = matches / len(lore_elements)

    # More lenient threshold for initial lore learning
    assert (
        consistency_score > 0.1
    ), f"Lore consistency too low: {consistency_score}. AI is learning lore elements."


@pytest.mark.integration
@pytest.mark.validation
def test_ai_output_completeness_real_ai(orchestrator):
    """Test that AI outputs are complete and not truncated."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI completeness test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    result = orchestrator.run_turn(player_choice_id="1")

    scene = result.get("scene", "")
    assert not scene.endswith("...")
    assert not scene.endswith(" .")

    narrative = result.get("narrative", "")
    assert not narrative.endswith("...")

    options = result.get("event", {}).get("options", [])
    for i, option in enumerate(options):
        text = option.get("text", "")
        assert not text.endswith("...")
        assert len(text) > 5
