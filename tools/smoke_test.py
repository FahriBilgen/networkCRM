#!/usr/bin/env python3
import os
import json
from pathlib import Path
import traceback
import sys

# Ensure real-LM path chosen if available
os.environ.setdefault("FORTRESS_USE_OLLAMA", "1")

# Add project root to path so package imports resolve when running from tools/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fortress_director.orchestrator.orchestrator import Orchestrator
from fortress_director.settings import DEFAULT_WORLD_STATE, SETTINGS


def run_once(max_turns=3):
    # Ensure world state file is reset to defaults to avoid immediate finalization
    # and force glitch metric to 0 for deterministic smoke runs
    try:
        path = SETTINGS.world_state_path
        state = DEFAULT_WORLD_STATE.copy()
        state["metrics"]["glitch"] = 0  # Override for deterministic tests
        path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
    orch = Orchestrator.build_default()

    # Initialize glitch_manager by running a dummy turn
    try:
        orch.run_turn()
    except Exception:
        pass  # Ignore errors, just to initialize

    # Override glitch manager to prevent triggered losses in smoke tests
    def no_loss(**kwargs):
        return {"roll": 0, "effects": [], "triggered_loss": False}

    orch.glitch_manager.resolve_turn = no_loss
    summary = {
        "turns": 0,
        "finalized": False,
        "win_loss": None,
        "major_events": 0,
        "safe_functions_executed": 0,
        "player_views": [],
    }
    try:
        for i in range(max_turns):
            res = orch.run_turn()
            summary["turns"] += 1
            wl = res.get("win_loss", {})
            summary["win_loss"] = wl
            if res.get("major_event_effect"):
                summary["major_events"] += 1
            sfs = res.get("safe_function_results") or []
            summary["safe_functions_executed"] += len(sfs)
            pv = res.get("player_view") or {}
            summary["player_views"].append(
                {
                    "turn": i + 1,
                    "short_scene": pv.get("short_scene", "")[:200],
                    "primary_reaction": pv.get("primary_reaction", "")[:200],
                }
            )
            if wl and wl.get("status") != "ongoing":
                summary["finalized"] = True
                break
    except Exception as exc:
        summary["error"] = str(exc)
        summary["traceback"] = traceback.format_exc()
    return summary


if __name__ == "__main__":
    runs = []
    for run_i in range(3):
        print(f"=== Starting smoke run {run_i + 1} ===")
        s = run_once(max_turns=10)
        runs.append(s)
        print(json.dumps(s, ensure_ascii=False, indent=2))
    # Write summary to runs/latest_smoke.json
    outp = Path("runs")
    outp.mkdir(exist_ok=True)
    Path(outp / "latest_smoke.json").write_text(
        json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("=== Smoke runs completed ===")
