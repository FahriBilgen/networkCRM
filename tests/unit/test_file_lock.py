"""Tests for file locking utilities."""

import os
import tempfile
import time
from pathlib import Path

import pytest

from fortress_director.utils.file_lock import (
    FileLock,
    file_lock,
    session_lock_path,
    session_state_path,
)


class TestFileLock:
    """Test FileLock class."""

    def test_file_lock_creates_lock_file(self):
        """FileLock should create a lock file on acquisition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock = FileLock(lock_path)

            assert not lock_path.exists()
            assert lock.acquire()
            assert lock_path.exists()
            lock.release()
            assert not lock_path.exists()

    def test_file_lock_context_manager(self):
        """FileLock should work as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock = FileLock(lock_path)

            assert not lock_path.exists()
            with lock:
                assert lock_path.exists()
            assert not lock_path.exists()

    def test_file_lock_timeout(self):
        """FileLock should timeout if lock is held."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock1 = FileLock(lock_path, timeout=0.5, poll_interval=0.1)
            lock2 = FileLock(lock_path, timeout=0.5, poll_interval=0.1)

            assert lock1.acquire()
            start = time.time()
            result = lock2.acquire()
            elapsed = time.time() - start

            assert not result  # Should timeout
            assert elapsed >= 0.5  # Should wait full timeout
            lock1.release()

    def test_file_lock_no_timeout(self):
        """FileLock with timeout=0 should not wait."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock1 = FileLock(lock_path, timeout=0.0)
            lock2 = FileLock(lock_path, timeout=0.0)

            assert lock1.acquire()
            result = lock2.acquire()
            assert not result  # Should fail immediately
            lock1.release()

    def test_file_lock_context_manager_failure(self):
        """FileLock context manager should raise TimeoutError on failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock1 = FileLock(lock_path, timeout=0)

            lock1.acquire()

            lock2 = FileLock(lock_path, timeout=0)
            with pytest.raises(TimeoutError):
                with lock2:
                    pass

            lock1.release()

    def test_file_lock_double_release(self):
        """FileLock should handle double release gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock = FileLock(lock_path)

            assert lock.acquire()
            lock.release()
            lock.release()  # Should not raise
            assert not lock_path.exists()

    def test_file_lock_stale_lock_recovery(self):
        """FileLock should recover from stale locks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            # Create a stale lock file (manually)
            lock_path.touch()
            old_time = time.time() - 400  # 6+ minutes old
            os.utime(str(lock_path), (old_time, old_time))

            # New lock should succeed despite stale lock
            lock = FileLock(lock_path, timeout=1.0, poll_interval=0.1)
            assert lock.acquire()
            lock.release()


class TestFileLockContextManager:
    """Test file_lock context manager function."""

    def test_file_lock_context_manager_function(self):
        """file_lock() should provide context management."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"

            assert not lock_path.exists()
            with file_lock(lock_path):
                assert lock_path.exists()
            assert not lock_path.exists()

    def test_file_lock_context_manager_timeout(self):
        """file_lock() should raise TimeoutError on timeout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "test.lock"
            lock1 = FileLock(lock_path)
            lock1.acquire()

            with pytest.raises(TimeoutError):
                with file_lock(lock_path, timeout=0.1):
                    pass

            lock1.release()


class TestSessionLockPath:
    """Test session_lock_path function."""

    def test_session_lock_path_generation(self):
        """session_lock_path should generate valid lock path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            session_id = "test_session_123"

            lock_path = session_lock_path(session_id, base_dir)

            assert lock_path.parent == base_dir
            assert ".lock." in str(lock_path)
            assert "test_session_123" in str(lock_path)

    def test_session_lock_path_sanitizes_unsafe_chars(self):
        """session_lock_path should sanitize unsafe filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            session_id = "test/session:with*invalid?chars"

            lock_path = session_lock_path(session_id, base_dir)

            # Should be valid filename (no /, :, *, ?)
            assert "/" not in str(lock_path.name)
            assert ":" not in str(lock_path.name)
            assert "*" not in str(lock_path.name)
            assert "?" not in str(lock_path.name)

    def test_session_lock_path_creates_directory(self):
        """session_lock_path should create base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "subdir" / "nested"
            session_id = "test_session"

            lock_path = session_lock_path(session_id, base_dir)

            assert base_dir.exists()


class TestSessionStatePath:
    """Test session_state_path function."""

    def test_session_state_path_generation(self):
        """session_state_path should generate valid state path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            session_id = "test_session_456"

            state_path = session_state_path(session_id, base_dir)

            assert state_path.parent == base_dir
            assert "state." in str(state_path)
            assert "test_session_456" in str(state_path)
            assert str(state_path).endswith(".json")

    def test_session_state_path_creates_directory(self):
        """session_state_path should create base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir) / "states" / "nested"
            session_id = "test_session"

            state_path = session_state_path(session_id, base_dir)

            assert base_dir.exists()

    def test_session_state_path_different_for_different_sessions(self):
        """Different sessions should have different state paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            path1 = session_state_path("session_1", base_dir)
            path2 = session_state_path("session_2", base_dir)

            assert path1 != path2
            assert "session_1" in str(path1)
            assert "session_2" in str(path2)


class TestSessionIsolation:
    """Integration tests for session isolation."""

    def test_multiple_sessions_can_hold_locks_sequentially(self):
        """Sessions should be able to acquire locks sequentially."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)

            # Session 1 lock
            lock_path_1 = session_lock_path("session_1", base_dir)
            with file_lock(lock_path_1, timeout=1.0):
                assert lock_path_1.exists()

            # Session 2 lock should work after session 1 releases
            lock_path_2 = session_lock_path("session_2", base_dir)
            with file_lock(lock_path_2, timeout=1.0):
                assert lock_path_2.exists()

    def test_session_lock_prevents_concurrent_access(self):
        """Session lock should prevent concurrent modifications."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            lock_path = session_lock_path("test_session", base_dir)

            # Hold lock in first context
            with file_lock(lock_path, timeout=0.1):
                # Try to acquire same lock should fail
                with pytest.raises(TimeoutError):
                    with file_lock(lock_path, timeout=0.1):
                        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
