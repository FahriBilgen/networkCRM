"""Performance caching layer for expensive computations."""

from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache, wraps
from typing import Any, Callable, Dict

LOGGER = logging.getLogger(__name__)

# Cache hit/miss statistics
_CACHE_STATS: Dict[str, Dict[str, int]] = {}


def _make_cache_key(args: tuple, kwargs: dict) -> str:
    """Create a hashable cache key from function arguments."""
    parts = []
    for arg in args[1:]:  # Skip self if method
        if isinstance(arg, (str, int, float, bool, type(None))):
            parts.append(str(arg))
        elif isinstance(arg, dict):
            parts.append(json.dumps(arg, sort_keys=True))
        elif hasattr(arg, "__dict__"):
            parts.append(json.dumps(arg.__dict__, sort_keys=True, default=str))
        else:
            parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        parts.append(f"{k}={v}")
    key_str = "|".join(parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached_computation(max_size: int = 128) -> Callable:
    """Decorator for caching expensive computations with stats tracking."""

    def decorator(func: Callable) -> Callable:
        cache: Dict[str, Any] = {}
        cache_info = {"hits": 0, "misses": 0}
        _CACHE_STATS[func.__name__] = cache_info

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                key = _make_cache_key(args, kwargs)
            except Exception as e:
                LOGGER.debug("Cache key generation failed: %s", e)
                return func(*args, **kwargs)

            if key in cache:
                cache_info["hits"] += 1
                return cache[key]

            result = func(*args, **kwargs)
            if len(cache) >= max_size:
                # Remove oldest entry (simple FIFO)
                cache.pop(next(iter(cache)))
            cache[key] = result
            cache_info["misses"] += 1
            return result

        def clear() -> None:
            cache.clear()
            cache_info["hits"] = 0
            cache_info["misses"] = 0

        wrapper.cache_clear = clear  # type: ignore
        wrapper.cache_info = cache_info  # type: ignore
        return wrapper

    return decorator


@lru_cache(maxsize=256)
def compute_threat_deltas(
    current_threat: int,
    event_intensity: int,
    morale: int,
) -> Dict[str, float]:
    """Cached threat computation.

    Maps threat + event + morale to predicted deltas.
    """
    if not (0 <= current_threat <= 100):
        return {"next_threat": float(current_threat)}

    # Simple threat model
    base_delta = event_intensity * 0.5
    morale_factor = max(0.1, morale / 100.0)
    adj_delta = base_delta * morale_factor

    return {
        "next_threat": float(current_threat + adj_delta),
        "change": float(adj_delta),
    }


@lru_cache(maxsize=256)
def compute_state_hash(state_json: str) -> str:
    """Cache state hash for identity comparisons."""
    return hashlib.sha256(state_json.encode()).hexdigest()


@lru_cache(maxsize=64)
def filter_available_functions(
    registry_size: int,
    enabled_mask: str,
) -> Dict[str, bool]:
    """Cache which functions are enabled given a mask."""
    # enabled_mask is a serialized JSON string of enabled functions
    try:
        return json.loads(enabled_mask)
    except json.JSONDecodeError:
        return {}


def get_cache_stats() -> Dict[str, Dict[str, int]]:
    """Return cache statistics for monitoring."""
    return {k: v.copy() for k, v in _CACHE_STATS.items()}


def clear_all_caches() -> None:
    """Clear all caches (useful for testing or theme switches)."""
    compute_threat_deltas.cache_clear()
    compute_state_hash.cache_clear()
    filter_available_functions.cache_clear()
    for cache_info in _CACHE_STATS.values():
        cache_info["hits"] = 0
        cache_info["misses"] = 0
    LOGGER.info("All performance caches cleared")
