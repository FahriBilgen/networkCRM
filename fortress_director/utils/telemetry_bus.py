"""Simple publisher/subscriber bus for turn telemetry streams."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any, AsyncGenerator, Dict, List, Optional


class TelemetryBus:
    """Fan-out helper used to expose SSE/polling telemetry feeds."""

    def __init__(self, max_history: int = 64) -> None:
        self._history: List[Dict[str, Any]] = []
        self._max_history = max_history
        self._subscribers: List[asyncio.Queue] = []

    def publish(self, payload: Dict[str, Any]) -> None:
        """Publish a telemetry entry to readers."""

        entry = dict(payload)
        entry.setdefault("timestamp", time.time())
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        for queue in list(self._subscribers):
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(entry)

    def latest(self) -> Optional[Dict[str, Any]]:
        """Return the most recent entry, if any."""

        if not self._history:
            return None
        return dict(self._history[-1])

    async def stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Async generator that yields telemetry events as they arrive."""

        queue: asyncio.Queue = asyncio.Queue(maxsize=16)
        self._subscribers.append(queue)
        try:
            # Replay last event immediately so late subscribers get context.
            if self._history:
                await queue.put(self._history[-1])
            while True:
                payload = await queue.get()
                yield dict(payload)
        finally:
            with contextlib.suppress(ValueError):
                self._subscribers.remove(queue)

