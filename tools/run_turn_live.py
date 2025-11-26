#!/usr/bin/env python3
"""Run a single game turn in-process using live LLMs (bypasses the HTTP API).

This script sets the runtime to use LLMs, loads the default theme, creates a
GameState and runs one turn through `run_turn`. Useful for quick local demos
when the HTTP server is difficult to keep running in this environment.
"""
from __future__ import annotations

import json
import sys

from fortress_director.llm.runtime_mode import set_llm_enabled
from fortress_director.themes.loader import BUILTIN_THEMES, load_theme_from_file
from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import run_turn


def main() -> int:
    # Ensure live LLM usage
    set_llm_enabled(True)

    # Load default theme from BUILTIN_THEMES mapping
    if not BUILTIN_THEMES:
        print("No builtin themes found.", file=sys.stderr)
        return 2
    # Pick the first theme available
    first_theme_id = next(iter(BUILTIN_THEMES))
    theme_path = BUILTIN_THEMES[first_theme_id]
    theme = load_theme_from_file(theme_path)

    # Create a fresh game state
    game_state = GameState.from_theme_config(theme)

    print(f"Running one turn with theme '{theme.id}' and live LLMs...")
    try:
        result = run_turn(
            game_state, player_choice=None, player_action_context=None, theme=theme
        )
    except Exception as exc:
        print(f"Turn execution failed: {exc}", file=sys.stderr)
        return 3

    out = {
        "narrative": result.narrative,
        "ui_events": [
            e.dict() if hasattr(e, "dict") else e
            for e in getattr(result, "ui_events", [])
        ],
        "turn_number": result.turn_number,
        "executed_actions": result.executed_actions,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
