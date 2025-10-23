"""Command-line entry point for running Fortress Director locally."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, cast

from orchestrator.orchestrator import (
    DEFAULT_WORLD_STATE,
    Orchestrator,
    StateStore,
)
from settings import SETTINGS


def _print_json(data: Dict[str, Any]) -> None:
    """Pretty-print JSON to stdout."""

    text = json.dumps(data, indent=2, ensure_ascii=False)
    sys.stdout.write(f"{text}\n")


def _parse_json_argument(raw: str | None, expected: type, label: str) -> Any:
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {exc}") from exc
    if not isinstance(data, expected):
        raise ValueError(f"{label} must decode to {expected.__name__}")
    return data


def _run_turn(choice_id: str | None) -> Dict[str, Any]:
    orchestrator = Orchestrator.build_default()
    return orchestrator.run_turn(player_choice_id=choice_id)


def _debug_state() -> Dict[str, Any]:
    store = StateStore(SETTINGS.world_state_path)
    return store.summary()


def _reset_state() -> None:
    payload = json.dumps(DEFAULT_WORLD_STATE, indent=2)
    SETTINGS.world_state_path.write_text(payload, encoding="utf-8")


def _handle_safe_call(args: argparse.Namespace) -> None:
    orchestrator = Orchestrator.build_default()
    try:
        args_payload = _parse_json_argument(
            args.args_json,
            list,
            "--args",
        )
        kwargs_payload = _parse_json_argument(
            args.kwargs_json,
            dict,
            "--kwargs",
        )
        metadata = _parse_json_argument(
            args.metadata_json,
            dict,
            "--metadata",
        )
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(2)

    payload: Dict[str, Any] = {"name": args.name}
    if args_payload is not None:
        payload["args"] = args_payload
    if kwargs_payload is not None:
        payload["kwargs"] = kwargs_payload
    if metadata is not None:
        payload["metadata"] = metadata

    try:
        result = orchestrator.run_safe_function(payload, metadata=metadata)
    except Exception as exc:  # pragma: no cover - surface to CLI user
        sys.stderr.write(f"Safe function call failed: {exc}\n")
        sys.exit(1)

    formatted = result if isinstance(result, dict) else {"result": result}
    _print_json(formatted)


def _handle_run(args: argparse.Namespace) -> None:
    result = _run_turn(args.choice_id)
    reactions = result.get("character_reactions", [])
    for reaction in reactions:
        effects = reaction.get("effects") or {}
        if effects:
            label = reaction.get("name", "unknown")
            sys.stdout.write(f"Effect summary [{label}]: {effects}\n")
    major_summary = result.get("major_event_effect_summary")
    if major_summary:
        sys.stdout.write(f"Major event impact: {major_summary}\n")
    _print_json(result)


def _handle_debug(_args: argparse.Namespace) -> None:
    summary = _debug_state()
    _print_json(summary)


def _handle_reset(_args: argparse.Namespace) -> None:
    _reset_state()
    sys.stdout.write("World state reset to defaults.\n")


def _normalise_log_level(level_name: str) -> int:
    candidate = (level_name or "INFO").upper()
    level = getattr(logging, candidate, None)
    if isinstance(level, int):
        return level
    return logging.INFO


def _prepare_log_file(filename: str | None) -> Path:
    SETTINGS.log_dir.mkdir(parents=True, exist_ok=True)
    if filename:
        path = Path(filename)
        if not path.is_absolute():
            path = SETTINGS.log_dir / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return SETTINGS.log_dir / f"turn_{timestamp}.log"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fortress Director CLI",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Console log level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        help="Optional log filename stored under the logs directory",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run_turn",
        help="Execute one deterministic game turn",
    )
    run_parser.add_argument(
        "--choice-id",
        dest="choice_id",
        help="ID of the player option to commit (defaults to first option)",
    )
    run_parser.set_defaults(handler=_handle_run)

    debug_parser = subparsers.add_parser(
        "debug_state",
        help="Print a summary of the persisted world state",
    )
    debug_parser.set_defaults(handler=_handle_debug)

    reset_parser = subparsers.add_parser(
        "reset",
        help="Reset world_state.json to its default payload",
    )
    reset_parser.set_defaults(handler=_handle_reset)

    safe_parser = subparsers.add_parser(
        "safe_call",
        help="Execute a registered safe function",
    )
    safe_parser.add_argument(
        "name",
        help="Name of the safe function to invoke",
    )
    safe_parser.add_argument(
        "--args",
        dest="args_json",
        help="Optional JSON array of positional arguments",
    )
    safe_parser.add_argument(
        "--kwargs",
        dest="kwargs_json",
        help="Optional JSON object of keyword arguments",
    )
    safe_parser.add_argument(
        "--metadata",
        dest="metadata_json",
        help="Optional JSON object stored alongside the checkpoint",
    )
    safe_parser.set_defaults(handler=_handle_safe_call)

    return parser


def _configure_logging(level_name: str, log_file: str | None) -> Path:
    log_path = _prepare_log_file(log_file)
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console_level = _normalise_log_level(level_name)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    root.debug(
        "Logging configured (console level=%s, file=%s)",
        logging.getLevelName(console_level),
        log_path,
    )
    return log_path


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    log_path = _configure_logging(args.log_level, args.log_file)
    logging.getLogger(__name__).info("Detailed logs written to %s", log_path)
    handler = cast(
        Callable[[argparse.Namespace], None],
        getattr(args, "handler"),
    )
    handler(args)


if __name__ == "__main__":
    main()
