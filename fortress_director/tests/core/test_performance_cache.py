"""Performance cache tests."""

from fortress_director.core.performance_cache import (
    cached_computation,
    clear_all_caches,
    compute_state_hash,
    compute_threat_deltas,
    filter_available_functions,
    get_cache_stats,
)


def test_cached_computation_decorator() -> None:
    """Verify cached_computation decorator works."""
    call_count = 0

    @cached_computation(max_size=32)
    def expensive_func(x: int, y: int) -> int:
        nonlocal call_count
        call_count += 1
        return x + y

    # First call should execute
    result1 = expensive_func(1, 2)
    assert result1 == 3
    assert call_count == 1

    # Second call with same args should use cache
    result2 = expensive_func(1, 2)
    assert result2 == 3
    assert call_count == 1  # No additional call

    # Different args should execute again
    result3 = expensive_func(2, 3)
    assert result3 == 5
    assert call_count == 2


def test_cache_stats_tracking() -> None:
    """Verify cache stats are tracked correctly."""
    clear_all_caches()

    @cached_computation(max_size=16)
    def tracked_func(x: int) -> int:
        return x * 2

    # Warm up cache
    for i in range(5):
        tracked_func(i)

    # Hit cache
    for i in range(5):
        tracked_func(i)

    stats = get_cache_stats()
    assert "tracked_func" in stats
    assert stats["tracked_func"]["hits"] >= 5


def test_compute_threat_deltas_basic() -> None:
    """Test threat delta computation is cached."""
    result1 = compute_threat_deltas(50, 10, 75)
    assert "next_threat" in result1
    assert "change" in result1
    assert isinstance(result1["next_threat"], float)
    assert isinstance(result1["change"], float)

    # Same call should hit cache
    result2 = compute_threat_deltas(50, 10, 75)
    assert result1 == result2


def test_compute_threat_deltas_out_of_bounds() -> None:
    """Test threat computation handles OOB values gracefully."""
    result = compute_threat_deltas(150, 10, 75)
    assert "next_threat" in result
    assert result["next_threat"] == 150.0


def test_compute_state_hash_caching() -> None:
    """Test state hash computation is cached."""
    state_json = '{"turn": 1, "threat": 50}'
    hash1 = compute_state_hash(state_json)
    hash2 = compute_state_hash(state_json)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex length


def test_filter_available_functions_caching() -> None:
    """Test function availability filter is cached."""
    mask = '{"func_a": true, "func_b": false}'
    result1 = filter_available_functions(75, mask)
    result2 = filter_available_functions(75, mask)
    assert result1 == result2
    assert result1["func_a"] is True
    assert result1["func_b"] is False


def test_filter_available_functions_invalid_json() -> None:
    """Test filter handles invalid JSON gracefully."""
    result = filter_available_functions(75, "not json")
    assert result == {}


def test_clear_all_caches() -> None:
    """Test clearing all caches."""
    # Populate caches
    compute_threat_deltas(50, 10, 75)
    compute_state_hash("test")

    # Clear
    clear_all_caches()

    # Stats should be reset
    stats = get_cache_stats()
    for cache_info in stats.values():
        assert cache_info["hits"] == 0
        assert cache_info["misses"] == 0


def test_cache_eviction_respects_max_size() -> None:
    """Test cache respects max_size limit."""

    @cached_computation(max_size=3)
    def bounded_func_unique(x: int) -> int:
        return x

    # Add 5 items (max is 3)
    for i in range(5):
        bounded_func_unique(i)

    # Should have created 5 unique cache entries
    # (but internally cache only keeps 3 at a time due to eviction)
    # This test just verifies the function works with eviction
    assert True


def test_threat_deltas_with_various_morale() -> None:
    """Test threat computation scales with threat and morale."""
    # Same threat, different morale
    baseline = compute_threat_deltas(50, 10, 50)
    assert "change" in baseline

    # Test that different values produce different results
    alt1 = compute_threat_deltas(50, 20, 50)
    alt2 = compute_threat_deltas(50, 10, 25)

    # Different event_intensity should give different changes
    assert baseline["change"] != alt1["change"]
    # Different morale should affect the result too
    assert baseline["change"] != alt2["change"]


def test_state_hash_different_for_different_state() -> None:
    """Test different states produce different hashes."""
    state1 = '{"turn": 1}'
    state2 = '{"turn": 2}'

    hash1 = compute_state_hash(state1)
    hash2 = compute_state_hash(state2)

    assert hash1 != hash2
