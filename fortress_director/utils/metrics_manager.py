"""Metric management utilities for the packaged orchestrator."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, MutableMapping, Optional

LOGGER = logging.getLogger(__name__)


MetricDict = MutableMapping[str, Any]


@dataclass
class MetricManager:
    """Centralised helper responsible for metric mutation and logging."""

    state: Dict[str, Any]
    log_sink: Optional[List[Dict[str, Any]]] = None
    _metrics: MetricDict = field(init=False, repr=False)

    CORE_DEFAULTS: Dict[str, int] = field(
        default_factory=lambda: {
            "order": 50,
            "morale": 50,
            "resources": 40,
            "knowledge": 45,
            "corruption": 10,
            "glitch": 12,
        }
    )

    LEGACY_DEFAULTS: Dict[str, int] = field(
        default_factory=lambda: {
            "risk_applied_total": 0,
            "major_flag_set": False,
            "major_events_triggered": 0,
            "major_event_last_turn": None,
        }
    )

    LIMITS: Dict[str, tuple[int, int]] = field(
        default_factory=lambda: {
            "order": (0, 100),
            "morale": (0, 100),
            "resources": (0, 120),
            "knowledge": (0, 100),
            "corruption": (0, 100),
            "glitch": (0, 100),
        }
    )

    def __post_init__(self) -> None:
        metrics = self.state.setdefault("metrics", {})
        for key, value in self.CORE_DEFAULTS.items():
            metrics.setdefault(key, value)
        for key, value in self.LEGACY_DEFAULTS.items():
            metrics.setdefault(key, value)
        self._metrics = metrics
        if self.log_sink is None:
            self.log_sink = metrics.setdefault("_log_buffer", [])
        LOGGER.debug("MetricManager initialised with metrics: %s", self.snapshot())

    def snapshot(self, *, include_legacy: bool = True) -> Dict[str, Any]:
        if include_legacy:
            keys: Iterable[str] = self._metrics.keys()
        else:
            keys = self.CORE_DEFAULTS.keys()
        snapshot: Dict[str, Any] = {}
        for key in keys:
            if isinstance(key, str) and key.startswith("_"):
                continue
            snapshot[key] = self._metrics.get(key)
        return snapshot

    def value(self, metric: str) -> int:
        raw = self._metrics.get(metric, 0)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    def adjust_metric(self, metric: str, delta: int, *, cause: str) -> int:
        if not metric:
            raise ValueError("metric name is required")
        current = self.value(metric)
        limit = self.LIMITS.get(metric, (0, 9999))
        LOGGER.debug(
            "Adjusting metric '%s': current=%s, delta=%s, limits=%s (cause=%s)",
            metric,
            current,
            delta,
            limit,
            cause,
        )
        updated = self._clamp(current + int(delta), limit)
        self._metrics[metric] = updated
        self._log_change(metric, updated - current, updated, cause)
        LOGGER.info(
            "Metric '%s' updated from %s to %s (cause=%s)",
            metric,
            current,
            updated,
            cause,
        )
        return updated

    def modify_resources(self, amount: int, *, cause: str) -> int:
        return self.adjust_metric("resources", int(amount), cause=cause)

    def recover_metric(self, metric: str, amount: int, *, cause: str) -> int:
        """Recover (reduce) a metric by a positive amount."""
        return self.adjust_metric(metric, -int(amount), cause=cause)

    def apply_bulk(self, changes: Iterable[tuple[str, int, str]]) -> None:
        for metric, delta, cause in changes:
            LOGGER.debug(
                "Applying bulk metric change: metric=%s, delta=%s, cause=%s",
                metric,
                delta,
                cause,
            )
            self.adjust_metric(metric, delta, cause=cause)

    def _clamp(self, value: int, limit: tuple[int, int]) -> int:
        lower, upper = limit
        clamped = max(lower, min(upper, value))
        if clamped != value:
            LOGGER.debug(
                "Clamped metric value from %s to %s within bounds %s",
                value,
                clamped,
                limit,
            )
        return clamped

    def _log_change(self, metric: str, delta: int, value: int, cause: str) -> None:
        entry = {
            "metric": metric,
            "delta": delta,
            "value": value,
            "cause": cause,
        }
        if isinstance(self.log_sink, list):
            self.log_sink.append(entry)
        LOGGER.debug("Metric change logged: %s", entry)
