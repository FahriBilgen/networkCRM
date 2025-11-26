"""Environment validation and health check utilities."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

LOGGER = logging.getLogger(__name__)

# Application version
__version__ = "0.3.0"
_START_TIME = datetime.now(timezone.utc)


@dataclass
class HealthStatus:
    """Health status response."""

    status: str  # "ok", "degraded", "error"
    version: str
    uptime_seconds: float
    timestamp: str
    checks: Dict[str, Any]
    errors: list[str]


class EnvironmentValidator:
    """Validate required environment configuration."""

    @staticmethod
    def validate() -> tuple[bool, list[str]]:
        """Validate environment and return (success, errors)."""
        errors: list[str] = []

        # Check for optional database path
        db_path = os.getenv("FORTRESS_DB_PATH")
        if db_path and not Path(db_path).parent.exists():
            errors.append(f"DB_PATH parent doesn't exist: {db_path}")

        # Check for data directory
        data_dir = Path("data")
        if not data_dir.exists():
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
                LOGGER.info("Created data directory")
            except OSError as e:
                errors.append(f"Cannot create data dir: {e}")

        # Check for database directory
        db_dir = Path("db")
        if not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
                LOGGER.info("Created db directory")
            except OSError as e:
                errors.append(f"Cannot create db dir: {e}")

        # Check for logs directory
        logs_dir = Path("logs")
        if not logs_dir.exists():
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
                LOGGER.info("Created logs directory")
            except OSError as e:
                errors.append(f"Cannot create logs dir: {e}")

        # Validate writeable paths
        for path_name, path_obj in [
            ("data", data_dir),
            ("db", db_dir),
            ("logs", logs_dir),
        ]:
            test_file = path_obj / f".fortress_test_{os.getpid()}"
            try:
                test_file.write_text("test")
                test_file.unlink()
                LOGGER.debug("%s directory is writable", path_name)
            except OSError as e:
                errors.append(f"{path_name} not writable: {e}")

        # Check for required themes
        themes_dir = Path("fortress_director/themes/builtin")
        if not themes_dir.exists():
            errors.append(f"Themes directory missing: {themes_dir}")

        return (len(errors) == 0, errors)

    @staticmethod
    def get_checks() -> Dict[str, Any]:
        """Get detailed environment checks."""
        checks: Dict[str, Any] = {}

        # Python version
        import sys

        py_version = (
            f"{sys.version_info.major}."
            f"{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        )
        checks["python_version"] = py_version

        # Data directories
        for path_name, path_obj in [
            ("data_dir", Path("data")),
            ("db_dir", Path("db")),
            ("logs_dir", Path("logs")),
        ]:
            checks[path_name] = {
                "exists": path_obj.exists(),
                "writable": path_obj.is_dir() and os.access(path_obj, os.W_OK),
            }

        # Database
        from fortress_director.db.session_store import get_session_store

        try:
            _ = get_session_store()
            checks["database"] = {"connected": True, "sessions_table": True}
        except Exception as e:
            checks["database"] = {
                "connected": False,
                "error": str(e),
            }

        # Themes
        from fortress_director.themes.loader import BUILTIN_THEMES

        checks["themes"] = {
            "count": len(BUILTIN_THEMES),
            "default_available": "siege_default" in BUILTIN_THEMES,
        }

        # Safe functions
        from fortress_director.core.function_registry import load_defaults

        try:
            funcs = load_defaults()
            checks["safe_functions"] = {
                "count": len(funcs),
                "categories": len(set(m.category for m in funcs.values())),
            }
        except Exception as e:
            checks["safe_functions"] = {"error": str(e)}

        return checks


def get_health_status() -> HealthStatus:
    """Get current application health status."""
    env_ok, env_errors = EnvironmentValidator.validate()
    checks = EnvironmentValidator.get_checks()

    now = datetime.now(timezone.utc)
    uptime = (now - _START_TIME).total_seconds()

    status = "ok" if env_ok else "degraded"
    if env_errors:
        status = "error" if len(env_errors) > 2 else "degraded"

    return HealthStatus(
        status=status,
        version=__version__,
        uptime_seconds=uptime,
        timestamp=now.isoformat(),
        checks=checks,
        errors=env_errors,
    )
