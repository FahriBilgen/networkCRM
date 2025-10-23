"""Transactional rollback system for safe world state mutations."""

from __future__ import annotations

import logging
from collections import deque
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, Iterator, Optional

from .function_registry import FunctionCall


LOGGER = logging.getLogger(__name__)


class RollbackSystemError(RuntimeError):
    """Base exception for rollback errors."""


class NoCheckpointError(RollbackSystemError):
    """Raised when no checkpoints are available for rollback."""


@dataclass(frozen=True)
class WorldStateCheckpoint:
    """Snapshot of the world state captured for rollback."""

    state: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    call: FunctionCall | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", deepcopy(self.state))
        object.__setattr__(self, "metadata", deepcopy(self.metadata))

    @property
    def turn(self) -> Optional[int]:
        """Return the turn number stored in the snapshot, if present."""

        value = self.state.get("turn")
        return value if isinstance(value, int) else None

    def snapshot(self) -> Dict[str, Any]:
        """Return a deep copy of the stored state."""

        return deepcopy(self.state)


class RollbackSystem:
    """Manage checkpoints and restore previous world states on failure."""

    def __init__(
        self,
        snapshot_provider: Callable[[], Dict[str, Any]],
        restore_callback: Callable[[Dict[str, Any]], None],
        *,
        max_checkpoints: int | None = 5,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        if max_checkpoints is not None and max_checkpoints < 1:
            raise ValueError("max_checkpoints must be positive or None")
        self._snapshot_provider = snapshot_provider
        self._restore_callback = restore_callback
        self._max_checkpoints = max_checkpoints
        self._history: Deque[WorldStateCheckpoint] = deque()
        self._logger = logger or LOGGER

    def create_checkpoint(
        self,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        call: FunctionCall | None = None,
    ) -> WorldStateCheckpoint:
        """Capture the current world state and push it onto the stack."""

        snapshot = self._snapshot_provider()
        # pragma: no cover - defensive guard
        if not isinstance(snapshot, dict):
            raise RollbackSystemError("Snapshot provider must return a dict")
        checkpoint = WorldStateCheckpoint(
            state=snapshot,
            metadata=metadata or {},
            call=call,
        )
        if (
            self._max_checkpoints is not None
            and len(self._history) >= self._max_checkpoints
        ):
            dropped = self._history.popleft()
            LOGGER.info("Dropped oldest checkpoint (turn=%s)", dropped.turn)
        self._history.append(checkpoint)
        LOGGER.info(
            "Checkpoint created (turn=%s, call=%s)",
            checkpoint.turn,
            checkpoint.call.name if checkpoint.call else None,
        )
        return checkpoint

    def rollback(
        self,
        *,
        reason: Optional[str] = None,
    ) -> WorldStateCheckpoint:
        """Restore to the most recent checkpoint and return it."""

        LOGGER.info("Rollback requested (reason=%s)", reason)
        if not self._history:
            LOGGER.error("No checkpoints available for rollback!")
            raise NoCheckpointError("No checkpoints available for rollback")
        checkpoint = self._history.pop()
        self._restore_callback(checkpoint.snapshot())
        LOGGER.info(
            "Rollback applied (turn=%s, reason=%s)",
            checkpoint.turn,
            reason or "unspecified",
        )
        return checkpoint

    def rollback_to(
        self,
        checkpoint: WorldStateCheckpoint,
        *,
        reason: Optional[str] = None,
    ) -> WorldStateCheckpoint:
        """Restore to the specific checkpoint if present in history."""

        buffer: Deque[WorldStateCheckpoint] = deque()
        target: Optional[WorldStateCheckpoint] = None
        while self._history:
            current = self._history.pop()
            if current == checkpoint and target is None:
                target = current
                break
            buffer.appendleft(current)
        self._history.extend(buffer)
        if target is None:
            raise NoCheckpointError("Checkpoint not found in history")
        self._restore_callback(target.snapshot())
        self._logger.warning(
            "Rollback applied to checkpoint (turn=%s, reason=%s)",
            target.turn,
            reason or "unspecified",
        )
        return target

    def clear(self) -> None:
        """Remove all checkpoints from history."""

        self._history.clear()

    def has_checkpoints(self) -> bool:
        """Return whether the history contains any checkpoints."""

        return bool(self._history)

    def latest_checkpoint(self) -> WorldStateCheckpoint:
        """Return the most recent checkpoint without restoring it."""

        if not self._history:
            raise NoCheckpointError("No checkpoints available")
        return self._history[-1]

    def iter_history(self) -> Iterator[WorldStateCheckpoint]:
        """Iterate over checkpoints from oldest to newest."""

        return iter(tuple(self._history))

    @contextmanager
    def transaction(
        self,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        call: FunctionCall | None = None,
    ) -> Iterator[WorldStateCheckpoint]:
        """Context manager that rolls back on exception."""

        checkpoint = self.create_checkpoint(metadata=metadata, call=call)
        try:
            yield checkpoint
        except Exception as exc:  # pragma: no cover - narrow exception scope
            self.rollback(
                reason=f"Exception during transaction: {exc!r}",
            )
            raise

    def run_validated_call(
        self,
        validator: "FunctionCallValidator",
        payload: Dict[str, Any],
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Validate and execute a safe function with rollback guarantees."""

        call = validator.validate(payload)
        checkpoint_metadata = dict(metadata or {})
        checkpoint_metadata.setdefault("call_name", call.name)
        checkpoint_metadata.setdefault("call_metadata", call.metadata)
        checkpoint = self.create_checkpoint(
            metadata=checkpoint_metadata,
            call=call,
        )
        entry = validator.registry.get(call.name)
        try:
            LOGGER.info("Executing safe function '%s'...", call.name)
            result = entry.function(*call.args, **call.kwargs)
            LOGGER.info("Safe function '%s' executed successfully.", call.name)
        except Exception as exc:
            validator.revert_record(call.name)
            reason = f"Execution failed for '{call.name}': {exc.__class__.__name__}"
            LOGGER.error("Safe function '%s' failed: %s", call.name, exc, exc_info=True)
            self.rollback(reason=reason)
            raise
        LOGGER.info(
            "Safe function '%s' executed (checkpoint turn=%s)",
            call.name,
            checkpoint.turn,
        )
        if self._history and self._history[-1] is checkpoint:
            self._history.pop()
        return result


# Local import to avoid circular dependency during import time.
from .function_validator import FunctionCallValidator  # noqa: E402
