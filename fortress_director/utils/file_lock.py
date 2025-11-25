"""File locking utilities for session isolation."""

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional


class FileLock:
    """
    Simple file-based lock for session isolation.

    Ensures only one process can access a session's state at a time.
    Uses lock files with timeout to prevent deadlocks.
    """

    def __init__(
        self,
        lock_path: Path,
        timeout: float = 30.0,
        poll_interval: float = 0.01,
    ):
        """
        Initialize file lock.

        Args:
            lock_path: Path to lock file
            timeout: Maximum seconds to wait for lock (0=no wait)
            poll_interval: Seconds between lock acquisition attempts
        """
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._lock_acquired = False

    def acquire(self) -> bool:
        """
        Acquire the lock.

        Returns:
            True if lock acquired, False if timeout
        """
        start_time = time.time()

        while True:
            # Try to create lock file exclusively
            try:
                # Use os.open with O_CREAT | O_EXCL for atomic operation
                fd = os.open(
                    str(self.lock_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o644,
                )
                os.close(fd)
                self._lock_acquired = True
                return True
            except FileExistsError:
                # Lock file exists, check if we've timed out
                elapsed = time.time() - start_time
                if self.timeout is not None and self.timeout > 0:
                    if elapsed > self.timeout:
                        return False
                elif self.timeout == 0:
                    # timeout=0 means fail immediately
                    return False

                # Check for stale lock (older than 5 minutes)
                if self._is_stale():
                    try:
                        os.remove(str(self.lock_path))
                        continue  # Retry after removing stale lock
                    except OSError:
                        pass  # Another process removed it

                # Wait before retrying
                time.sleep(self.poll_interval)

    def release(self) -> None:
        """Release the lock."""
        if not self._lock_acquired:
            return

        try:
            os.remove(str(self.lock_path))
        except OSError:
            pass  # Lock already gone

        self._lock_acquired = False

    def _is_stale(self) -> bool:
        """Check if lock file is stale (older than 5 minutes)."""
        try:
            mtime = os.path.getmtime(str(self.lock_path))
            age_seconds = time.time() - mtime
            return age_seconds > 300  # 5 minutes
        except OSError:
            return False

    def __enter__(self) -> "FileLock":
        """Context manager entry."""
        if not self.acquire():
            raise TimeoutError(
                f"Failed to acquire lock: {self.lock_path} "
                f"(timeout={self.timeout}s)"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.release()


@contextmanager
def file_lock(
    lock_path: Path,
    timeout: float = 30.0,
    poll_interval: float = 0.01,
) -> Generator[None, None, None]:
    """
    Context manager for file-based locking.

    Args:
        lock_path: Path to lock file
        timeout: Maximum seconds to wait for lock
        poll_interval: Seconds between lock acquisition attempts

    Yields:
        None

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
    """
    lock = FileLock(lock_path, timeout, poll_interval)
    with lock:
        yield


def session_lock_path(session_id: str, base_dir: Path) -> Path:
    """
    Generate lock file path for a session.

    Args:
        session_id: Session identifier
        base_dir: Base directory for lock files

    Returns:
        Path to session lock file
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    # Sanitize session_id to make it safe for filenames
    safe_session_id = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in session_id
    )
    return base_dir / f".lock.{safe_session_id}"


def session_state_path(session_id: str, base_dir: Path) -> Path:
    """
    Generate state file path for a session.

    Args:
        session_id: Session identifier
        base_dir: Base directory for state files

    Returns:
        Path to session state file
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    # Use session_id directly for state files
    return base_dir / f"state.{session_id}.json"
