"""Metric management utilities for deterministic turn processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, MutableMapping, Optional


MetricDict = MutableMapping[str, Any]


@dataclass
class MetricManager:
    """Centralised helper responsible for metric mutation and logging."""

    state: Dict[str, Any]
    log_sink: Optional[List[Dict[str, Any]]] = None
    _metrics: MetricDict = field(init=False, repr=False)

    #: Core gameplay metrics with their default starting values.
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

    #: Legacy counters preserved for backwards compatibility.
    LEGACY_DEFAULTS: Dict[str, int] = field(
        default_factory=lambda: {
            "risk_applied_total": 0,
            "major_flag_set": False,
            "major_events_triggered": 0,
            "major_event_last_turn": None,
        }
    )

    #: Clamp boundaries for each mutable metric.
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
            # Stand-alone operations fall back to per-state rolling log list.
            self.log_sink = metrics.setdefault("_log_buffer", [])

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def snapshot(self, *, include_legacy: bool = True) -> Dict[str, Any]:
        """Return a shallow copy of the managed metrics."""

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
        """Fetch the current value for *metric* (defaults to zero)."""

        raw = self._metrics.get(metric, 0)
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    def adjust_metric(self, metric: str, delta: int, *, cause: str) -> int:
        """Apply *delta* to *metric* and return the clamped result."""

        if not metric:
            raise ValueError("metric name is required")

        current = self.value(metric)
        limit = self.LIMITS.get(metric, (0, 9999))
        updated = self._clamp(current + int(delta), limit)
        self._metrics[metric] = updated
        self._log_change(metric, updated - current, updated, cause)
        return updated

    def modify_resources(self, amount: int, *, cause: str) -> int:
        """Adjust resources by *amount* (alias for :meth:`adjust_metric`)."""

        return self.adjust_metric("resources", int(amount), cause=cause)

    def apply_bulk(self, changes: Iterable[tuple[str, int, str]]) -> None:
        """Apply a batch of metric updates."""

        for metric, delta, cause in changes:
            self.adjust_metric(metric, delta, cause=cause)

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    def _clamp(self, value: int, limit: tuple[int, int]) -> int:
        lower, upper = limit
        return max(lower, min(upper, value))

    def _log_change(self, metric: str, delta: int, value: int, cause: str) -> None:
        entry = {
            "metric": metric,
            "delta": delta,
            "value": value,
            "cause": cause,
        }
        if isinstance(self.log_sink, list):
            self.log_sink.append(entry)

