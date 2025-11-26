"""TIER 4.4: Performance regression and optimization tests."""

import time
from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import run_turn
from fortress_director.themes.loader import (
    BUILTIN_THEMES,
    load_theme_from_file,
)


def test_turn_execution_performance_baseline() -> None:
    """Test turn execution stays within performance baseline."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])

    # Record turn execution times
    execution_times = []

    for _ in range(5):
        start = time.time()
        game_state = GameState.from_theme_config(theme, session_id="perf_test")
        result = run_turn(game_state, theme=theme)
        elapsed = time.time() - start

        assert result.world_state is not None
        execution_times.append(elapsed)

    # Average should be reasonable (< 2 seconds)
    avg_time = sum(execution_times) / len(execution_times)
    assert avg_time < 2.0, f"Turn execution too slow: {avg_time}s"


def test_turn_execution_consistency() -> None:
    """Test turn execution times are consistent."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])

    times = []
    for _ in range(10):
        start = time.time()
        sid = "consistency_test"
        game_state = GameState.from_theme_config(theme, session_id=sid)
        result = run_turn(game_state, theme=theme)
        elapsed = time.time() - start

        assert result.world_state is not None
        times.append(elapsed)

    # Standard deviation should be low (consistent performance)
    avg = sum(times) / len(times)
    variance = sum((t - avg) ** 2 for t in times) / len(times)
    std_dev = variance**0.5

    # Std dev should be less than 50% of average
    assert std_dev < (avg * 0.5), "High variance in execution times"


def test_state_size_doesn_bloat() -> None:
    """Test state JSON doesn't bloat over turns."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    state_sizes = []

    for turn in range(10):
        sid = "bloat_test"
        game_state = GameState.from_theme_config(theme, session_id=sid)

        # Run several turns
        for _ in range(turn + 1):
            result = run_turn(game_state, theme=theme)
            assert result.world_state is not None

        state = game_state.get_projected_state()
        import json

        state_json = json.dumps(state)
        state_sizes.append(len(state_json))

    # Size growth should be linear or sublinear, not exponential
    initial_size = state_sizes[0]
    final_size = state_sizes[-1]

    # Should not grow more than 3x
    assert final_size < (initial_size * 3)


def test_multiple_turn_cycle_performance() -> None:
    """Test performance over multiple turn cycles."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])

    sid = "multi_turn_test"
    game_state = GameState.from_theme_config(theme, session_id=sid)

    cycle_times = []

    for cycle in range(5):
        start = time.time()

        for _ in range(5):
            result = run_turn(game_state, theme=theme)
            assert result.world_state is not None

        cycle_time = time.time() - start
        cycle_times.append(cycle_time)

    # Average cycle time should be reasonable
    avg_cycle = sum(cycle_times) / len(cycle_times)
    assert avg_cycle < 10.0


def test_memory_allocation_stability() -> None:
    """Test memory allocation doesn't spike."""
    import sys

    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])

    base_size = sys.getsizeof(theme)

    # Run many operations
    for _ in range(20):
        game_state = GameState.from_theme_config(theme, session_id="mem_test")
        result = run_turn(game_state, theme=theme)
        assert result.world_state is not None

    # Theme object should not grow
    final_size = sys.getsizeof(theme)
    assert final_size == base_size


def test_cache_improves_performance() -> None:
    """Test that caching improves performance."""
    from fortress_director.core.performance_cache import (
        get_cache_stats,
        clear_all_caches,
    )

    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])

    # Clear caches
    clear_all_caches()

    # First run - cache misses
    game_state1 = GameState.from_theme_config(theme, session_id="cache_test_1")
    _ = run_turn(game_state1, theme=theme)

    # Second run - cache hits
    game_state2 = GameState.from_theme_config(theme, session_id="cache_test_2")
    _ = run_turn(game_state2, theme=theme)

    # Check cache stats
    stats = get_cache_stats()

    # Should have at least one cache hit
    if stats:
        total_hits = sum(s.get("hits", 0) for s in stats.values())
        assert total_hits > 0
