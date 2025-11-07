"""Centralised logging configuration for Fortress Director."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional, Union

from fortress_director.utils.archive_manager import compress_pattern

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _normalise_level(level: Union[str, int, None], *, default: int) -> int:
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        candidate = getattr(logging, level.upper(), None)
        if isinstance(candidate, int):
            return candidate
        try:
            return int(level)
        except ValueError:
            return default
    return default


def _parse_logger_overrides(raw: Optional[str]) -> Dict[str, int]:
    overrides: Dict[str, int] = {}
    if not raw:
        return overrides
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            name, level_str = token.split(":", 1)
        else:
            name, level_str = token, "WARNING"
        overrides[name.strip()] = _normalise_level(
            level_str.strip(), default=logging.WARNING
        )
    return overrides


def configure_logging(
    *,
    console_level: Union[str, int, None] = None,
    file_level: Union[str, int, None] = None,
    log_path: Optional[Union[str, Path]] = None,
    force: bool = False,
    quiet_loggers: Optional[Dict[str, Union[str, int]]] = None,
) -> Path:
    """Configure root logging handlers once and return the active log path.

    Args:
        console_level: Desired console logging level (string or int).
        file_level: Desired file logging level (string or int).
        log_path: Optional explicit path for the rotating log file.
        force: When True, existing handlers are replaced.
        quiet_loggers: Optional mapping of logger names to their desired levels,
            applied after handler configuration. Environment variable
            FORTRESS_LOGGER_OVERRIDES can be used to supply additional overrides
            in the form ``module:LEVEL,module2:LEVEL``.
    """

    if getattr(configure_logging, "_configured", False) and not force:
        return Path(getattr(configure_logging, "_log_path"))

    console_env = os.getenv("FORTRESS_LOG_CONSOLE_LEVEL")
    file_env = os.getenv("FORTRESS_LOG_FILE_LEVEL")

    console_level_value = _normalise_level(console_level or console_env, default=logging.INFO)
    file_level_value = _normalise_level(file_level or file_env, default=logging.DEBUG)

    if log_path is not None:
        log_file_path = Path(log_path)
    else:
        path_override = os.getenv("FORTRESS_LOG_PATH")
        if path_override:
            log_file_path = Path(path_override)
        else:
            log_dir = os.getenv("FORTRESS_LOG_DIR")
            if log_dir:
                log_directory = Path(log_dir)
            else:
                log_directory = Path(__file__).resolve().parents[2] / "logs"
            log_directory.mkdir(parents=True, exist_ok=True)
            log_file_path = log_directory / "fortress_run.log"
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if force:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level_value)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=2_097_152,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(file_level_value)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Compress older run_* log files to keep the folder tidy.
    compress_pattern(log_file_path.parent, "run_*.log", keep=5)

    overrides = _parse_logger_overrides(os.getenv("FORTRESS_LOGGER_OVERRIDES"))
    if quiet_loggers:
        for name, level in quiet_loggers.items():
            overrides[name] = _normalise_level(level, default=logging.WARNING)
    for logger_name, level in overrides.items():
        logging.getLogger(logger_name).setLevel(level)

    root_logger.debug(
        "Logging configured (console=%s, file=%s, path=%s)",
        logging.getLevelName(console_level_value),
        logging.getLevelName(file_level_value),
        log_file_path,
    )

    configure_logging._configured = True  # type: ignore[attr-defined]
    configure_logging._log_path = str(log_file_path)  # type: ignore[attr-defined]
    return log_file_path


__all__ = ["configure_logging"]
