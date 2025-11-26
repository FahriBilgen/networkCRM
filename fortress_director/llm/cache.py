"""In-memory cache used to short-circuit repeated LLM prompts."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict

from fortress_director.settings import SETTINGS


@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: float


class LLMCache:
    """A very small TTL-based cache suitable for prompt responses."""

    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl = ttl_seconds
        self._store: Dict[str, CacheEntry] = {}

    def make_key(
        self,
        agent: str,
        model_name: str,
        prompt: str,
        extra: dict | None = None,
    ) -> str:
        payload = {
            "agent": agent,
            "model": model_name,
            "prompt": prompt,
            "extra": extra or {},
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() - entry.created_at > self.ttl:
            del self._store[key]
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = CacheEntry(key=key, value=value, created_at=time.time())


DEFAULT_CACHE = LLMCache(ttl_seconds=int(SETTINGS.llm_runtime.cache_ttl_seconds))


def get_default_cache() -> LLMCache:
    """Return the process-wide LLM cache instance."""

    return DEFAULT_CACHE


__all__ = ["LLMCache", "CacheEntry", "get_default_cache"]
