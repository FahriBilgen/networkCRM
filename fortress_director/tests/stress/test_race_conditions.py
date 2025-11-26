"""TIER 4.1: Race condition and advanced stress tests."""

import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Event
from typing import List
from uuid import uuid4

from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import run_turn
from fortress_director.themes.loader import (
    BUILTIN_THEMES,
    load_theme_from_file,
)


def test_race_condition_state_consistency() -> None:
    """Test concurrent modifications don't corrupt state."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    lock = Lock()
    final_states: List[dict] = []

    def modify_and_check(thread_id: int) -> None:
        sid = f"race_test_{thread_id}_{uuid4().hex}"
        game_state = GameState.from_theme_config(theme, session_id=sid)

        # Run 5 turns
        for turn in range(5):
            result = run_turn(game_state, theme=theme)
            assert result.world_state is not None

        # Store state safely
        with lock:
            final_states.append(game_state.get_projected_state())

    # 10 concurrent threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(modify_and_check, i) for i in range(10)]
        _ = [f.result() for f in futures]

    # All states should be valid
    assert len(final_states) == 10
    for state in final_states:
        assert state is not None


def test_barrier_synchronization() -> None:
    """Test synchronized multi-thread operations."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    start_event = Event()
    results: List[float] = []
    lock = Lock()

    def synchronized_run(thread_id: int) -> None:
        # Wait for all threads to be ready
        start_event.wait()
        start_time = time.time()

        sid = f"barrier_test_{thread_id}_{uuid4().hex}"
        game_state = GameState.from_theme_config(theme, session_id=sid)
        result = run_turn(game_state, theme=theme)

        elapsed = time.time() - start_time
        with lock:
            results.append(elapsed)

        assert result.world_state is not None

    # Create 8 threads all waiting
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(synchronized_run, i) for i in range(8)]

        # Give threads time to reach barrier
        time.sleep(0.1)

        # Release all at once
        start_event.set()

        _ = [f.result() for f in futures]

    # All should complete
    assert len(results) == 8
    # Times should be relatively close (within 5 seconds)
    assert max(results) - min(results) < 5.0


def test_thundering_herd() -> None:
    """Test system handles sudden spike in requests."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    barrier_event = Event()
    completed = 0
    lock = Lock()

    def herd_request(req_id: int) -> bool:
        nonlocal completed
        barrier_event.wait()  # Wait at barrier

        sid = f"herd_{req_id}_{uuid4().hex}"
        try:
            game_state = GameState.from_theme_config(theme, session_id=sid)
            result = run_turn(game_state, theme=theme)
            with lock:
                completed += 1
            return result.world_state is not None
        except Exception:
            return False

    # Queue up 50 requests
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = [executor.submit(herd_request, i) for i in range(50)]

        # Wait a bit then unleash
        time.sleep(0.2)
        barrier_event.set()
        results = [f.result() for f in futures]

    # Should handle the spike
    assert completed >= 40  # At least 80% should succeed
    assert sum(results) >= 40


def test_cascade_failure_prevention() -> None:
    """Test one error doesn't cascade to other sessions."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    successful = 0
    failed = 0
    lock = Lock()

    def potentially_failing_run(run_id: int) -> bool:
        nonlocal successful, failed
        sid = f"cascade_test_{run_id}_{uuid4().hex}"

        try:
            game_state = GameState.from_theme_config(theme, session_id=sid)
            _ = run_turn(game_state, theme=theme)

            with lock:
                successful += 1
            return True
        except Exception:
            with lock:
                failed += 1
            return False

    # 30 concurrent runs
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(potentially_failing_run, i) for i in range(30)]
        _ = [f.result() for f in futures]

    # Most should succeed despite any individual failures
    assert successful >= 20


def test_session_leakage_prevention() -> None:
    """Verify no session state leaks between users."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    session_map: dict = {}
    lock = Lock()

    def isolated_session_run(user_id: int) -> str:
        sid = f"user_{user_id}_{uuid4().hex}"

        # Create and run 3 turns
        game_state = GameState.from_theme_config(theme, session_id=sid)
        for _ in range(3):
            result = run_turn(game_state, theme=theme)
            assert result.world_state is not None

        # Store session info
        state = game_state.get_projected_state()
        with lock:
            session_map[sid] = {
                "user_id": user_id,
                "turn": state.get("turn"),
            }

        return sid

    # 15 concurrent users
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(isolated_session_run, i) for i in range(15)]
        session_ids = [f.result() for f in futures]

    # All sessions should be unique
    assert len(set(session_ids)) == 15

    # Each should have correct turn count
    for sid, info in session_map.items():
        assert info["turn"] == 3


def test_thread_pool_exhaustion_handling() -> None:
    """Test system degrades gracefully with thread pool exhaustion."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    completed = 0
    lock = Lock()

    def long_running_task(task_id: int) -> bool:
        nonlocal completed
        sid = f"pool_test_{task_id}_{uuid4().hex}"

        try:
            game_state = GameState.from_theme_config(theme, session_id=sid)
            for _ in range(2):
                result = run_turn(game_state, theme=theme)
                assert result.world_state is not None

            with lock:
                completed += 1
            return True
        except Exception:
            return False

    # Use smaller pool to test queueing
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(long_running_task, i) for i in range(20)]
        results = [f.result() for f in futures]

    # All should eventually complete
    assert completed == 20
    assert all(results)


def test_variable_load_handling() -> None:
    """Test system handles varying request loads."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    phases = [5, 15, 30, 15, 5]  # Load ramp up and down
    total_completed = 0

    for phase_num, load in enumerate(phases):

        def phase_request(req_id: int) -> bool:
            sid = f"phase_{phase_num}_req_{req_id}_{uuid4().hex}"
            try:
                game_state = GameState.from_theme_config(theme, session_id=sid)
                result = run_turn(game_state, theme=theme)
                return result.world_state is not None
            except Exception:
                return False

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(phase_request, i) for i in range(load)]
            results = [f.result() for f in futures]
            total_completed += sum(results)

    # Most requests should succeed across all phases
    assert total_completed >= 60  # Out of 70 total
