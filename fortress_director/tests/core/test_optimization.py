"""TIER 4.4: Advanced optimization tests."""

import tempfile
from pathlib import Path
import sqlite3

from fortress_director.core.optimization import (
    DatabaseOptimizer,
    ConnectionPool,
    QueryOptimizer,
    AsyncOptimizationStrategy,
    get_db_optimizer,
)


def test_database_optimizer_creation() -> None:
    """Test DatabaseOptimizer can be created."""
    optimizer = DatabaseOptimizer()
    assert optimizer is not None


def test_database_indexes_creation() -> None:
    """Test database indexes are created correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create test database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS game_sessions "
            "(session_id TEXT, created_at TIMESTAMP)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS game_state "
            "(id INTEGER, session_id TEXT, turn_number INTEGER, "
            "timestamp TIMESTAMP)"
        )
        conn.commit()
        conn.close()

        # Create indexes
        DatabaseOptimizer.create_indexes(str(db_path))

        # Verify indexes exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert any("session_id" in idx for idx in indexes)
        assert any("turn" in idx for idx in indexes)


def test_optimization_stats() -> None:
    """Test optimization stats are generated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create minimal database
        conn = sqlite3.connect(db_path)
        conn.close()

        stats = DatabaseOptimizer.get_optimization_stats(str(db_path))

        assert "page_count" in stats
        assert "page_size" in stats
        assert "db_size_bytes" in stats
        assert stats["page_size"] > 0


def test_connection_pool_creation() -> None:
    """Test connection pool can be created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        sqlite3.connect(db_path).close()  # Create empty DB

        pool = ConnectionPool(db_path, pool_size=3)
        assert pool is not None
        pool.close_all()


def test_connection_pool_get_connection() -> None:
    """Test getting connection from pool."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        sqlite3.connect(db_path).close()

        pool = ConnectionPool(db_path, pool_size=2)

        conn1 = pool.get_connection()
        assert conn1 is not None

        conn2 = pool.get_connection()
        assert conn2 is not None
        assert conn1 != conn2

        pool.close_all()


def test_connection_pool_return_connection() -> None:
    """Test returning connection to pool."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        sqlite3.connect(db_path).close()

        pool = ConnectionPool(db_path, pool_size=2)

        conn = pool.get_connection()
        pool.return_connection(conn)

        # Should be able to get it again
        conn2 = pool.get_connection()
        assert conn == conn2

        pool.close_all()


def test_connection_pool_stats() -> None:
    """Test connection pool statistics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        sqlite3.connect(db_path).close()

        pool = ConnectionPool(db_path, pool_size=5)

        stats = pool.get_stats()
        assert stats["pool_size"] == 5
        assert stats["available"] == 5
        assert stats["in_use"] == 0

        conn = pool.get_connection()
        stats = pool.get_stats()
        assert stats["available"] == 4
        assert stats["in_use"] == 1

        pool.return_connection(conn)
        stats = pool.get_stats()
        assert stats["available"] == 5

        pool.close_all()


def test_query_optimizer_session_lookup() -> None:
    """Test optimized session lookup query."""
    query = QueryOptimizer.optimize_session_lookup_query()

    assert "SELECT" in query
    assert "game_sessions" in query
    assert "LEFT JOIN" in query
    assert "COUNT" in query


def test_query_optimizer_turn_history() -> None:
    """Test optimized turn history query."""
    query = QueryOptimizer.optimize_turn_history_query()

    assert "SELECT" in query
    assert "ORDER BY turn_number DESC" in query
    assert "LIMIT" in query
    assert "OFFSET" in query


def test_query_optimizer_batch_insert() -> None:
    """Test batch insert query generation."""
    query = QueryOptimizer.optimize_batch_insert_query(
        "test_table", ["col1", "col2"], batch_size=5
    )

    assert "INSERT INTO test_table" in query
    assert "VALUES" in query
    # Should have 5 value sets
    assert query.count("(?,?)") == 5


def test_async_optimization_should_use_async() -> None:
    """Test async optimization decision."""
    should_use = AsyncOptimizationStrategy.should_use_async_turn_execution()
    assert isinstance(should_use, bool)


def test_async_optimization_batch_size() -> None:
    """Test optimal batch size."""
    batch_size = AsyncOptimizationStrategy.get_optimal_batch_size()
    assert batch_size > 0
    assert batch_size <= 100


def test_async_optimization_max_concurrent() -> None:
    """Test max concurrent turns."""
    max_concurrent = AsyncOptimizationStrategy.get_max_concurrent_turns()
    assert max_concurrent > 0
    assert max_concurrent <= 10


def test_global_optimizer_instance() -> None:
    """Test global optimizer instance."""
    opt1 = get_db_optimizer()
    opt2 = get_db_optimizer()

    # Should be same instance
    assert opt1 is opt2
