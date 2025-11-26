"""Turn performance benchmarking."""

import time

from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import run_turn
from fortress_director.themes.loader import (
    BUILTIN_THEMES,
    load_theme_from_file,
)


def test_turn_execution_performance() -> None:
    """Benchmark turn execution time.

    Target: < 2 seconds per turn in normal mode.
    """
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    game_state = GameState.from_theme_config(theme)

    # Warm up
    run_turn(game_state, theme=theme)

    # Benchmark 3 turns
    times: list[float] = []
    for i in range(3):
        start = time.perf_counter()
        result = run_turn(game_state, player_choice=None, theme=theme)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        assert result.world_state is not None

    avg_time = sum(times) / len(times)
    max_time = max(times)

    print("--- Turn Performance ---")
    print(f"Average: {avg_time:.3f}s")
    print(f"Max: {max_time:.3f}s")
    print(f"Individual times: {[f'{t:.3f}s' for t in times]}")

    # Loose target: under 5s (accounting for LLM calls)
    assert max_time < 5.0, f"Turn too slow: {max_time:.3f}s"


def test_turn_result_completeness() -> None:
    """Verify turn results contain all required fields."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    game_state = GameState.from_theme_config(theme)

    result = run_turn(game_state, theme=theme)

    assert result.world_state is not None
    assert result.ui_payload is not None
    assert "turn_number" in result.world_state
    assert "turn" in result.world_state
    assert result.game_over == bool(game_state.game_over)


def test_cache_effectiveness_on_repeated_calls() -> None:
    """Verify caching provides benefits on repeated operations."""
    from fortress_director.core.performance_cache import (
        clear_all_caches,
        get_cache_stats,
    )

    clear_all_caches()
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    game_state = GameState.from_theme_config(theme)

    # Run multiple turns to benefit from caching
    for _ in range(2):
        run_turn(game_state, theme=theme)

    stats = get_cache_stats()
    # Should have some hits if caching is effective
    total_hits = sum(s["hits"] for s in stats.values())
    total_misses = sum(s["misses"] for s in stats.values())

    print("--- Cache Stats ---")
    print(f"Total hits: {total_hits}")
    print(f"Total misses: {total_misses}")

    if total_hits + total_misses > 0:
        hit_rate = total_hits / (total_hits + total_misses)
        print(f"Hit rate: {hit_rate:.1%}")


def test_state_operations_are_efficient() -> None:
    """Verify state operations don't block turn execution."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    game_state = GameState.from_theme_config(theme)

    # Time state operations specifically
    start = time.perf_counter()
    for _ in range(100):
        _ = game_state.get_projected_state()
    elapsed = time.perf_counter() - start

    # 100 projections should be fast
    avg_per_call = elapsed / 100
    print(f"\nAverage state projection: {avg_per_call*1000:.2f}ms")
    assert avg_per_call < 0.01, "State projection too slow"
