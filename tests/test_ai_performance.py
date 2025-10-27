"""AI Performance Testing for Fortress Director.

Tests real AI model performance, response times, and quality metrics.
"""

import os
import time
import pytest
from typing import Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from fortress_director.orchestrator.orchestrator import Orchestrator, StateStore
from fortress_director.agents.event_agent import EventAgent
from fortress_director.agents.world_agent import WorldAgent
from fortress_director.agents.character_agent import CharacterAgent
from fortress_director.agents.judge_agent import JudgeAgent


@dataclass
class PerformanceMetrics:
    """Performance metrics for AI model evaluation."""

    response_time: float
    token_count: int = 0
    quality_score: float = 0.0
    consistency_score: float = 0.0
    model_name: str = ""


class AIPerformanceTester:
    """Test harness for AI model performance evaluation."""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []

    def measure_response_time(self, func, *args, **kwargs) -> tuple:
        """Measure execution time of a function call."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        response_time = end_time - start_time
        return result, response_time

    def evaluate_output_quality(self, output: Any, expected_keys: List[str]) -> float:
        """Evaluate output quality based on structure and completeness."""
        if isinstance(output, list) and len(output) > 0:
            # Handle list outputs (like CharacterAgent)
            return self._evaluate_list_quality(output, expected_keys)
        elif isinstance(output, dict):
            return self._evaluate_dict_quality(output, expected_keys)
        return 0.0

    def _evaluate_dict_quality(
        self, output: Dict[str, Any], expected_keys: List[str]
    ) -> float:
        """Evaluate dict output quality."""
        if not isinstance(output, dict):
            return 0.0

        score = 0.0
        total_keys = len(expected_keys)

        for key in expected_keys:
            if key in output:
                score += 1.0
                # Bonus for non-empty values
                value = output[key]
                if isinstance(value, (str, list)) and len(value) > 0:
                    score += 0.5
                elif isinstance(value, dict) and len(value) > 0:
                    score += 0.5

        return min(score / total_keys, 1.0) if total_keys > 0 else 0.0

    def _evaluate_list_quality(
        self, output: List[Any], expected_keys: List[str]
    ) -> float:
        """Evaluate list output quality."""
        if not isinstance(output, list) or len(output) == 0:
            return 0.0

        # For lists, check if first item has expected structure
        first_item = output[0]
        if isinstance(first_item, dict):
            return self._evaluate_dict_quality(first_item, expected_keys)
        return 0.0


@pytest.fixture
def orchestrator(tmp_path: Path) -> Orchestrator:
    """Create orchestrator for testing."""
    # Create orchestrator with runs_dir
    orchestrator = Orchestrator.__new__(Orchestrator)
    from fortress_director.rules.rules_engine import RulesEngine
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
@pytest.mark.performance
def test_event_agent_performance_real_ai():
    """Test EventAgent performance with real AI models."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI performance test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    tester = AIPerformanceTester()
    agent = EventAgent()

    # Test input
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

    # Measure performance
    result, response_time = tester.measure_response_time(agent.generate, test_input)

    # Evaluate quality
    quality_score = tester.evaluate_output_quality(
        result, ["scene", "options", "major_event"]
    )

    # Record metrics
    metrics = PerformanceMetrics(
        response_time=response_time,
        quality_score=quality_score,
        model_name="event_agent_model",
    )
    tester.metrics.append(metrics)

    # Assertions
    assert response_time < 60.0, f"EventAgent response too slow: {response_time}s"
    assert quality_score > 0.5, f"EventAgent output quality too low: {quality_score}"
    assert isinstance(result, dict), "EventAgent should return dict"
    assert "scene" in result, "EventAgent output missing scene"
    assert "options" in result, "EventAgent output missing options"


@pytest.mark.integration
@pytest.mark.performance
def test_world_agent_performance_real_ai():
    """Test WorldAgent performance with real AI models."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI performance test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    tester = AIPerformanceTester()
    agent = WorldAgent()

    # Test input
    test_input = {
        "WORLD_CONTEXT": "Turn 1 | Day 1 | Time morning\nLocation: entrance\nPlayer: Test Player",
        "room": "entrance",
    }

    # Measure performance
    result, response_time = tester.measure_response_time(agent.describe, test_input)

    # Evaluate quality
    quality_score = tester.evaluate_output_quality(
        result, ["atmosphere", "sensory_details"]
    )

    # Record metrics
    metrics = PerformanceMetrics(
        response_time=response_time,
        quality_score=quality_score,
        model_name="world_agent_model",
    )
    tester.metrics.append(metrics)

    # Assertions
    assert response_time < 30.0, f"WorldAgent response too slow: {response_time}s"
    assert quality_score > 0.5, f"WorldAgent output quality too low: {quality_score}"
    assert isinstance(result, dict), "WorldAgent should return dict"
    assert "atmosphere" in result, "WorldAgent output missing atmosphere"


@pytest.mark.integration
@pytest.mark.performance
def test_character_agent_performance_real_ai():
    """Test CharacterAgent performance with real AI models."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI performance test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    tester = AIPerformanceTester()
    agent = CharacterAgent()

    # Test input
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

    # Measure performance
    result, response_time = tester.measure_response_time(agent.react, test_input)

    # Evaluate quality
    quality_score = tester.evaluate_output_quality(
        result, ["name", "intent", "action", "speech"]
    )

    # Record metrics
    metrics = PerformanceMetrics(
        response_time=response_time,
        quality_score=quality_score,
        model_name="character_agent_model",
    )
    tester.metrics.append(metrics)

    # Assertions
    assert response_time < 45.0, f"CharacterAgent response too slow: {response_time}s"
    assert (
        quality_score > 0.5
    ), f"CharacterAgent output quality too low: {quality_score}"
    assert isinstance(result, list), "CharacterAgent should return list"
    assert len(result) > 0, "CharacterAgent should return non-empty list"


@pytest.mark.integration
@pytest.mark.performance
def test_judge_agent_performance_real_ai():
    """Test JudgeAgent performance with real AI models."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI performance test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    tester = AIPerformanceTester()
    agent = JudgeAgent()

    # Test input
    test_input = {
        "WORLD_CONTEXT": "Test world context",
        "content": '{"scene": "test scene", "player_choice": {"text": "test choice"}, "character_update": {"name": "TestNPC", "intent": "test", "action": "test action", "speech": "test speech"}}',
    }

    # Measure performance
    result, response_time = tester.measure_response_time(agent.evaluate, test_input)

    # Evaluate quality
    quality_score = tester.evaluate_output_quality(result, ["consistent", "reason"])

    # Record metrics
    metrics = PerformanceMetrics(
        response_time=response_time,
        quality_score=quality_score,
        model_name="judge_agent_model",
    )
    tester.metrics.append(metrics)

    # Assertions
    assert response_time < 30.0, f"JudgeAgent response too slow: {response_time}s"
    assert quality_score > 0.5, f"JudgeAgent output quality too low: {quality_score}"
    assert isinstance(result, dict), "JudgeAgent should return dict"
    assert "consistent" in result, "JudgeAgent output missing consistent field"


@pytest.mark.integration
@pytest.mark.performance
def test_full_turn_performance_real_ai(orchestrator: Orchestrator):
    """Test full turn performance with real AI models."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI performance test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    tester = AIPerformanceTester()

    # Measure full turn performance
    start_time = time.time()
    result = orchestrator.run_turn(player_choice_id="1")
    end_time = time.time()
    response_time = end_time - start_time

    # Evaluate overall quality
    quality_score = tester.evaluate_output_quality(
        result, ["WORLD_CONTEXT", "scene", "options", "character_events", "win_loss"]
    )

    # Record metrics
    metrics = PerformanceMetrics(
        response_time=response_time,
        quality_score=quality_score,
        model_name="full_turn_orchestrator",
    )
    tester.metrics.append(metrics)

    # Assertions
    assert response_time < 180.0, f"Full turn too slow: {response_time}s"
    assert quality_score > 0.6, f"Full turn quality too low: {quality_score}"
    assert isinstance(result, dict), "Full turn should return dict"
    assert "scene" in result, "Full turn missing scene"
    assert "win_loss" in result, "Full turn missing win_loss"


@pytest.mark.integration
@pytest.mark.performance
def test_ai_model_consistency_real_ai(orchestrator: Orchestrator):
    """Test AI model output consistency across multiple runs."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip(
            "Skipping real AI consistency test; set FORTRESS_USE_OLLAMA=1 to run"
        )

    tester = AIPerformanceTester()
    consistency_scores = []

    # Run multiple turns and measure consistency
    for i in range(3):
        start_time = time.time()
        result = orchestrator.run_turn(player_choice_id="1")
        end_time = time.time()
        response_time = end_time - start_time

        # Basic quality check
        quality_score = tester.evaluate_output_quality(
            result, ["scene", "options", "win_loss"]
        )

        # Consistency check (all outputs should have similar structure)
        has_scene = "scene" in result and isinstance(result["scene"], str)
        has_options = "options" in result and isinstance(result["options"], list)
        has_win_loss = "win_loss" in result and isinstance(result["win_loss"], dict)

        consistency_score = 1.0 if (has_scene and has_options and has_win_loss) else 0.0
        consistency_scores.append(consistency_score)

        # Record metrics
        metrics = PerformanceMetrics(
            response_time=response_time,
            quality_score=quality_score,
            consistency_score=consistency_score,
            model_name=f"consistency_run_{i+1}",
        )
        tester.metrics.append(metrics)

        assert (
            response_time < 180.0
        ), f"Consistency run {i+1} too slow: {response_time}s"
        assert (
            quality_score > 0.5
        ), f"Consistency run {i+1} quality too low: {quality_score}"

    # Overall consistency check
    avg_consistency = sum(consistency_scores) / len(consistency_scores)
    assert avg_consistency > 0.8, f"AI consistency too low: {avg_consistency}"


# Performance benchmark fixtures
@pytest.fixture
def performance_tester():
    """Provide AIPerformanceTester instance for benchmarks."""
    return AIPerformanceTester()


@pytest.mark.benchmark
def test_event_agent_benchmark(benchmark, performance_tester):
    """Benchmark EventAgent performance."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip("Skipping benchmark; set FORTRESS_USE_OLLAMA=1 to run")

    agent = EventAgent()
    test_input = {
        "WORLD_CONTEXT": "Benchmark test context",
        "day": 1,
        "time": "morning",
        "room": "entrance",
        "recent_events": "none",
        "world_constraint_from_prev_turn": {"atmosphere": "clear"},
        "recent_motifs": "none",
        "lore_continuity_weight": 0,
        "memory_layers": [],
    }

    def run_benchmark():
        result, response_time = performance_tester.measure_response_time(
            agent.generate, test_input
        )
        return result

    result = benchmark(run_benchmark)

    # Basic validation
    assert isinstance(result, dict)
    assert "scene" in result
    assert "options" in result
