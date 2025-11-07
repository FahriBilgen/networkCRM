"""Command-line entry point for running Fortress Director locally."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fortress_director.utils.logging_config import configure_logging
from fortress_director.orchestrator.orchestrator import (
    DEFAULT_WORLD_STATE,
    Orchestrator,
    StateStore,
)
from fortress_director.settings import SETTINGS
from fortress_director.utils.theme_loader import (
    ThemeConfig,
    ThemeError,
    build_world_state_for_theme,
    load_theme_package,
)
try:  # pragma: no cover - optional dependency
    from fortress_director.llm.offline_client import OfflineOllamaClient
except ImportError:  # pragma: no cover - fallback when stub absent
    OfflineOllamaClient = None  # type: ignore[assignment]


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


def _run_turn(choice_id: str | None, orchestrator: Orchestrator) -> Dict[str, Any]:
    return orchestrator.run_turn(player_choice_id=choice_id)


def _debug_state() -> Dict[str, Any]:
    store = StateStore(SETTINGS.world_state_path)
    return store.summary()


def _reset_state() -> None:
    payload = json.dumps(deepcopy(DEFAULT_WORLD_STATE), indent=2)
    SETTINGS.world_state_path.write_text(payload, encoding="utf-8")


def _seed_theme_world_state(theme: ThemeConfig) -> None:
    themed_state = build_world_state_for_theme(
        theme,
        deepcopy(DEFAULT_WORLD_STATE),
    )
    payload = json.dumps(themed_state, indent=2, ensure_ascii=False)
    SETTINGS.world_state_path.write_text(payload, encoding="utf-8")


def _swap_offline_clients(orchestrator: Orchestrator) -> None:
    if OfflineOllamaClient is None:  # pragma: no cover - optional dependency
        logging.getLogger(__name__).warning(
            "OfflineOllamaClient unavailable; continuing with live models.",
        )
        return
    mappings = [
        ("event_agent", "event"),
        ("world_agent", "world"),
        ("creativity_agent", "creativity"),
        ("planner_agent", "planner"),
        ("director_agent", "director"),
        ("character_agent", "character"),
        ("judge_agent", "judge"),
    ]
    for attr, key in mappings:
        agent = getattr(orchestrator, attr, None)
        if agent is not None and hasattr(agent, "_client"):
            agent._client = OfflineOllamaClient(agent_key=key)


def _peek_options(orchestrator: Orchestrator) -> List[Dict[str, Any]]:
    """Compute current turn's options without committing a choice.

    Runs a turn once to obtain options, then restores the previous state so
    the user can select an option that will be actually committed.
    """
    snapshot = orchestrator.state_store.snapshot()
    result = orchestrator.run_turn(player_choice_id=None)
    options: List[Dict[str, Any]] = []
    raw = result.get("options") if isinstance(result, dict) else None
    if isinstance(raw, list):
        options = [opt for opt in raw if isinstance(opt, dict)]
    # Restore to snapshot so we can commit the real choice next
    orchestrator.state_store.persist(snapshot)
    return options


def _handle_safe_call(args: argparse.Namespace) -> None:
    theme: Optional[ThemeConfig] = getattr(args, "_theme_config", None)
    if theme is not None:
        _seed_theme_world_state(theme)
    orchestrator = Orchestrator.build_default(theme=theme)
    if getattr(args, "offline", True):
        _swap_offline_clients(orchestrator)
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


def _handle_run_cli(args: argparse.Namespace) -> None:
    """Run turns with optional interactive selection and clean state reset."""
    turns = max(1, getattr(args, "turns", 1))
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    run_dir = SETTINGS.project_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    theme: Optional[ThemeConfig] = getattr(args, "_theme_config", None)
    if theme is not None:
        _seed_theme_world_state(theme)
    elif getattr(args, "reset_before", False):
        _reset_state()
    orchestrator = Orchestrator.build_default(theme=theme)
    try:
        orchestrator.runs_dir = run_dir
    except Exception:
        pass

    interactive = bool(getattr(args, "interactive", False))
    for turn_index in range(turns):
        if getattr(args, "random_choices", False):
            import os as _os
            _os.environ["FORTRESS_RANDOM_CHOICES"] = "1"
            choice_id: Optional[str] = "__random__"
        elif interactive:
            options = _peek_options(orchestrator)
            choice_id = None
            if options:
                sys.stdout.write("\n=== Turn %d Options ===\n" % (turn_index + 1))
                for idx, opt in enumerate(options, start=1):
                    oid = str(opt.get("id", idx))
                    text = str(opt.get("text", ""))
                    sys.stdout.write(f"  [{idx}] {text} (id={oid})\n")
                sys.stdout.write("Select option number (or 'r' random, 'q' quit): ")
                user_in = input().strip()
                if user_in.lower() in {"q", "quit", "exit"}:
                    sys.stdout.write("Exiting interactive session.\n")
                    break
                if user_in.lower() in {"r", "rand", "random"}:
                    choice_id = "__random__"
                else:
                    try:
                        sel = int(user_in)
                        if 1 <= sel <= len(options):
                            choice_id = str(options[sel - 1].get("id") or sel)
                        else:
                            sys.stdout.write("Invalid index; defaulting to first option.\n")
                            choice_id = str(options[0].get("id") or "")
                    except ValueError:
                        choice_id = user_in
            else:
                sys.stdout.write("No options available; defaulting to engine choice.\n")
                choice_id = None
        else:
            choice_id = args.choice_id

        result = _run_turn(choice_id, orchestrator)
        results.append(result)
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
        output_path = run_dir / f"turn_{turn_index + 1:03d}.json"
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        if result.get("win_loss", {}).get("status") != "ongoing":
            break

    log_path = getattr(args, "_log_path", None)
    if isinstance(log_path, Path) and log_path.exists():
        shutil.copy2(log_path, run_dir / "run.log")

def _handle_run(args: argparse.Namespace) -> None:
    turns = max(1, getattr(args, "turns", 1))
    # Her çalıştırma için benzersiz zaman damgalı klasör oluştur
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    run_dir = SETTINGS.project_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    theme: Optional[ThemeConfig] = getattr(args, "_theme_config", None)
    if theme is not None:
        _seed_theme_world_state(theme)
    # Orchestrator'ı bir kez oluştur, run klasörünü ata
    orchestrator = Orchestrator.build_default(theme=theme)
    try:
        orchestrator.runs_dir = run_dir
    except Exception:
        pass
    for turn_index in range(turns):
        if getattr(args, "random_choices", False):
            import os as _os
            _os.environ["FORTRESS_RANDOM_CHOICES"] = "1"
            choice_id = "__random__"
        else:
            choice_id = args.choice_id
        result = _run_turn(choice_id, orchestrator)
        results.append(result)
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
        output_path = run_dir / f"turn_{turn_index + 1:03d}.json"
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        # Break if game concluded
        if result.get("win_loss", {}).get("status") != "ongoing":
            break

    # Bu süreçte kullanılan log dosyasını run klasörüne kopyala
    log_path = getattr(args, "_log_path", None)
    if isinstance(log_path, Path) and log_path.exists():
        # run.log ismiyle kopyala
        shutil.copy2(log_path, run_dir / "run.log")


def _handle_debug(_args: argparse.Namespace) -> None:
    summary = _debug_state()
    _print_json(summary)


def _handle_reset(_args: argparse.Namespace) -> None:
    _reset_state()
    sys.stdout.write("World state reset to defaults.\n")


def _handle_theme_validate(args: argparse.Namespace) -> None:
    try:
        theme = load_theme_package(args.identifier)
    except ThemeError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(1)
    summary = {
        "id": theme.id,
        "label": theme.label,
        "version": theme.version,
        "description": theme.description,
        "source_path": str(theme.source_path),
        "prompt_overrides": {k: str(v) for k, v in theme.prompt_paths.items()},
        "world_override_keys": sorted(theme.world_overrides.keys()),
        "safe_function_override_keys": sorted(theme.safe_function_overrides.keys()),
        "asset_keys": sorted(theme.assets.keys()),
    }
    _print_json(summary)


def _handle_theme_simulate(args: argparse.Namespace) -> None:
    try:
        theme = load_theme_package(args.identifier)
    except ThemeError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(1)

    orchestrator = Orchestrator.build_default(theme=theme)
    initial_state = orchestrator.state_store.snapshot()
    turns = max(1, getattr(args, "turns", 1))
    results: List[Dict[str, Any]] = []
    try:
        for turn_idx in range(turns):
            if getattr(args, "random_choices", False):
                os.environ["FORTRESS_RANDOM_CHOICES"] = "1"
                choice_id: Optional[str] = "__random__"
            else:
                choice_id = getattr(args, "choice_id", None)
            raw = _run_turn(choice_id, orchestrator)
            entry = {
                "turn": turn_idx + 1,
                "status": raw.get("win_loss", {}).get("status"),
                "turn_summary": raw.get("turn_summary"),
                "major_event": raw.get("major_event_effect_summary"),
            }
            if args.include_raw:
                entry["raw"] = raw
            results.append(entry)
            if raw.get("win_loss", {}).get("status") != "ongoing":
                break
    finally:
        if not getattr(args, "keep_state", False):
            orchestrator.state_store.persist(initial_state)

    report = {
        "theme": {
            "id": theme.id,
            "label": theme.label,
            "version": theme.version,
        },
        "turns_requested": turns,
        "turns_executed": len(results),
        "kept_state": bool(getattr(args, "keep_state", False)),
        "results": results,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _print_json(report)


def _handle_theme_sandbox(args: argparse.Namespace) -> None:
    try:
        theme = load_theme_package(args.identifier)
    except ThemeError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.exit(2)

    _seed_theme_world_state(theme)
    orchestrator = Orchestrator.build_default(theme=theme)
    if not getattr(args, "live_models", False):
        _swap_offline_clients(orchestrator)
    turns = max(1, getattr(args, "turns", 3))
    transcript: List[Dict[str, Any]] = []
    for turn_idx in range(turns):
        choice_id = "__random__" if getattr(args, "random_choices", True) else None
        result = orchestrator.run_turn(player_choice_id=choice_id)
        player_view = result.get("player_view") or {}
        transcript.append(
            {
                "turn": turn_idx + 1,
                "scene": result.get("scene", "")[:160],
                "choice": (result.get("player_choice") or {}).get("text"),
                "metrics": player_view.get("metrics_panel"),
                "safe_functions": [
                    sf.get("name") for sf in player_view.get("safe_function_history", [])
                ],
            }
        )
    print("=== Theme Sandbox Summary ===")
    print(f"Theme: {theme.label} ({theme.id}) | turns={turns}")
    for entry in transcript:
        print(f"\nTurn {entry['turn']}:")
        print(f"  Scene: {entry['scene']}")
        print(f"  Choice: {entry['choice']}")
        if entry["metrics"]:
            print(f"  Metrics: {entry['metrics']}")
        if entry["safe_functions"]:
            print(f"  Safe functions: {entry['safe_functions']}")


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
    # Varsayılan: zaman damgalı tekil log dosyası
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    return SETTINGS.log_dir / f"run_{timestamp}.log"


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
    parser.add_argument(
        "--theme",
        help="Theme id or JSON path (under ./themes) applied before running commands that mutate state",
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
    run_parser.add_argument(
        "--turns",
        type=int,
        default=1,
        help="Number of sequential turns to execute (default: 1)",
    )
    run_parser.add_argument(
        "--random-choices",
        action="store_true",
        help="Pick a random option each turn (simulates first-time play)",
    )
    run_parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode: peek and prompt each turn",
    )
    run_parser.add_argument(
        "--reset-before",
        action="store_true",
        help="Reset world state to defaults before starting",
    )
    run_parser.set_defaults(handler=_handle_run_cli)

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

    theme_parser = subparsers.add_parser(
        "theme",
        help="Validate or simulate theme packages",
    )
    theme_sub = theme_parser.add_subparsers(dest="theme_command", required=True)

    theme_validate = theme_sub.add_parser(
        "validate",
        help="Validate a theme file and print summary details",
    )
    theme_validate.add_argument(
        "identifier",
        help="Theme id or path to JSON file",
    )
    theme_validate.set_defaults(handler=_handle_theme_validate)

    theme_simulate = theme_sub.add_parser(
        "simulate",
        help="Seed a theme and run a limited turn preview",
    )
    theme_simulate.add_argument(
        "identifier",
        help="Theme id or path to JSON file",
    )
    theme_simulate.add_argument(
        "--turns",
        type=int,
        default=1,
        help="Number of turns to simulate (default: 1)",
    )
    theme_simulate.add_argument(
        "--choice-id",
        dest="choice_id",
        help="Specific option id to commit each turn",
    )
    theme_simulate.add_argument(
        "--random-choices",
        action="store_true",
        help="Pick a random option each turn",
    )
    theme_simulate.add_argument(
        "--include-raw",
        action="store_true",
        help="Include full turn payloads in the report",
    )
    theme_simulate.add_argument(
        "--keep-state",
        action="store_true",
        help="Keep the mutated state after simulation instead of restoring the snapshot",
    )
    theme_simulate.add_argument(
        "--output",
        type=Path,
        help="Optional JSON file to store the report",
    )
    theme_simulate.add_argument(
        "--live-models",
        dest="offline",
        action="store_false",
        help="Use configured live models instead of offline stubs",
    )
    theme_simulate.add_argument(
        "--offline",
        dest="offline",
        action="store_true",
        help="Force offline stub models (default behaviour)",
    )
    theme_simulate.set_defaults(offline=True)
    theme_simulate.set_defaults(handler=_handle_theme_simulate)

    theme_sandbox = theme_sub.add_parser(
        "sandbox",
        help="Run a lightweight sandbox session for designers",
    )
    theme_sandbox.add_argument(
        "identifier",
        help="Theme id or path to JSON file",
    )
    theme_sandbox.add_argument(
        "--turns",
        type=int,
        default=3,
        help="Number of turns to simulate (default: 3)",
    )
    theme_sandbox.add_argument(
        "--random-choices",
        action="store_true",
        help="Commit random options each turn (default).",
    )
    theme_sandbox.add_argument(
        "--live-models",
        action="store_true",
        help="Use live models instead of offline stubs.",
    )
    theme_sandbox.set_defaults(handler=_handle_theme_sandbox, random_choices=True)

    return parser


def _configure_logging(level_name: str, log_file: str | None) -> Path:
    log_path = _prepare_log_file(log_file)
    console_level = _normalise_log_level(level_name)
    configure_logging(
        console_level=console_level,
        file_level=logging.DEBUG,
        log_path=log_path,
        force=True,
    )
    logging.getLogger(__name__).debug(
        "Logging configured via CLI (console level=%s, path=%s)",
        logging.getLevelName(console_level),
        log_path,
    )
    return log_path


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    log_path = _configure_logging(args.log_level, args.log_file)
    theme_config: Optional[ThemeConfig] = None
    if getattr(args, "theme", None):
        try:
            theme_config = load_theme_package(args.theme)
        except ThemeError as exc:
            sys.stderr.write(f"{exc}\n")
            sys.exit(2)
    setattr(args, "_theme_config", theme_config)
    logging.getLogger(__name__).info("Detailed logs written to %s", log_path)
    # Handler'a log dosya yolunu geç, böylece run klasörüne kopyalanabilir
    setattr(args, "_log_path", log_path)
    handler = cast(
        Callable[[argparse.Namespace], None],
        getattr(args, "handler"),
    )
    handler(args)


if __name__ == "__main__":
    main()

