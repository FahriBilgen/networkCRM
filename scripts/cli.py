"""Lightweight CLI entry point for the three-agent pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fortress_director.core.state_store import GameState  # noqa: E402
from fortress_director.pipeline.turn_manager import run_turn  # noqa: E402

_CLI_GAME_STATE = GameState()


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _handle_run_turn(args: argparse.Namespace) -> Dict[str, Any]:
    choice_payload = {"id": args.choice} if args.choice else None
    result = run_turn(_CLI_GAME_STATE, player_choice=choice_payload)
    return result.to_dict()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fortress Director prototype CLI")
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging verbosity (default: INFO)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_turn_parser = subparsers.add_parser(
        "run_turn",
        help="Run a single turn through the pipeline",
    )
    run_turn_parser.add_argument(
        "--choice",
        dest="choice",
        help="Optional player choice identifier",
    )
    run_turn_parser.set_defaults(handler=_handle_run_turn)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)
    handler = getattr(args, "handler")
    payload = handler(args)
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
