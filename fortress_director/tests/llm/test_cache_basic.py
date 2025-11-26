from fortress_director.llm.cache import LLMCache


def test_cache_set_get_and_ttl_expiration() -> None:
    cache = LLMCache(ttl_seconds=1)
    key = cache.make_key("director", "mock-model", "prompt")
    assert cache.get(key) is None
    cache.set(key, {"payload": "ok"})
    assert cache.get(key) == {"payload": "ok"}
    # Expire the entry manually by rewinding created_at.
    cache._store[key].created_at -= 10  # type: ignore[attr-defined]
    assert cache.get(key) is None
