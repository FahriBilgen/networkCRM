"""Advanced optimization strategies for database and async operations."""

from typing import Optional
import sqlite3
from threading import Lock


class DatabaseOptimizer:
    """Optimizes database operations with indexes and connection pooling."""

    @staticmethod
    def create_indexes(db_path: str) -> None:
        """Create performance indexes on game_state database.

        Indexes for:
        - session_id lookups
        - timestamp range queries
        - turn number queries
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_sessions_session_id "
            "ON game_sessions(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_created "
            "ON game_sessions(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_state_turns " "ON game_state(turn_number)",
            "CREATE INDEX IF NOT EXISTS idx_state_session "
            "ON game_state(session_id, turn_number)",
            "CREATE INDEX IF NOT EXISTS idx_state_timestamp "
            "ON game_state(timestamp DESC)",
        ]

        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except sqlite3.OperationalError:
                pass  # Index may already exist

        # Vacuum to optimize after indexing
        cursor.execute("VACUUM")
        conn.commit()
        conn.close()

    @staticmethod
    def get_optimization_stats(db_path: str) -> dict:
        """Get database optimization statistics."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        stats = {}

        # Get page count
        cursor.execute("PRAGMA page_count")
        stats["page_count"] = cursor.fetchone()[0]

        # Get page size
        cursor.execute("PRAGMA page_size")
        stats["page_size"] = cursor.fetchone()[0]

        # Get free pages
        cursor.execute("PRAGMA freelist_count")
        stats["freelist_count"] = cursor.fetchone()[0]

        # Calculate database size
        stats["db_size_bytes"] = stats["page_count"] * stats["page_size"]
        stats["wasted_bytes"] = stats["freelist_count"] * stats["page_size"]

        conn.close()
        return stats


class ConnectionPool:
    """Simple connection pool for SQLite database connections."""

    def __init__(self, db_path: str, pool_size: int = 5) -> None:
        """Initialize connection pool."""
        self.db_path = db_path
        self.pool_size = pool_size
        self.connections: list[sqlite3.Connection] = []
        self.available: list[sqlite3.Connection] = []
        self.lock = Lock()
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize pool with connections."""
        for _ in range(self.pool_size):
            conn = sqlite3.connect(self.db_path)
            conn.isolation_level = None  # Autocommit mode
            self.connections.append(conn)
            self.available.append(conn)

    def get_connection(self, timeout: float = 5.0) -> sqlite3.Connection:
        """Get connection from pool with timeout."""
        import time

        start_time = time.time()

        while True:
            with self.lock:
                if self.available:
                    return self.available.pop()

            if time.time() - start_time > timeout:
                raise TimeoutError("No available connections in pool")

            time.sleep(0.1)

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """Return connection to pool."""
        with self.lock:
            if conn not in self.connections:
                return
            self.available.append(conn)

    def close_all(self) -> None:
        """Close all connections in pool."""
        for conn in self.connections:
            try:
                conn.close()
            except sqlite3.Error:
                pass

        self.connections.clear()
        self.available.clear()

    def get_stats(self) -> dict:
        """Get pool statistics."""
        with self.lock:
            return {
                "pool_size": self.pool_size,
                "available": len(self.available),
                "in_use": self.pool_size - len(self.available),
            }


class QueryOptimizer:
    """Optimizes common queries with caching and batching."""

    @staticmethod
    def optimize_session_lookup_query() -> str:
        """Generate optimized session lookup query."""
        return """
            SELECT s.session_id, s.created_at, COUNT(g.id) as turn_count
            FROM game_sessions s
            LEFT JOIN game_state g ON s.session_id = g.session_id
            WHERE s.session_id = ?
            GROUP BY s.session_id
        """

    @staticmethod
    def optimize_turn_history_query() -> str:
        """Generate optimized turn history query with limit."""
        return """
            SELECT id, session_id, turn_number, state_json, timestamp
            FROM game_state
            WHERE session_id = ?
            ORDER BY turn_number DESC
            LIMIT ? OFFSET ?
        """

    @staticmethod
    def optimize_batch_insert_query(
        table: str, columns: list[str], batch_size: int
    ) -> str:
        """Generate optimized batch insert query."""
        placeholders = ", ".join(["?"] * len(columns))
        values_list = ", ".join([f"({placeholders})"] * batch_size)
        cols_str = ", ".join(columns)
        return f"INSERT INTO {table} ({cols_str}) VALUES {values_list}"


class AsyncOptimizationStrategy:
    """Strategy for async operation optimization."""

    @staticmethod
    def should_use_async_turn_execution() -> bool:
        """Determine if async turn execution should be used."""
        return True  # Enable for production

    @staticmethod
    def should_batch_state_updates() -> bool:
        """Determine if state updates should be batched."""
        return True  # Enable for production

    @staticmethod
    def get_optimal_batch_size() -> int:
        """Get optimal batch size for state updates."""
        return 10  # Based on typical turn patterns

    @staticmethod
    def get_max_concurrent_turns() -> int:
        """Get max concurrent turn executions."""
        return 5  # Conservative limit for single-threaded SQLite


# Global optimization instance
_optimizer: Optional[DatabaseOptimizer] = None


def get_db_optimizer() -> DatabaseOptimizer:
    """Get database optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = DatabaseOptimizer()
    return _optimizer
