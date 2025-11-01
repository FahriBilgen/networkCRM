from __future__ import annotations

import json
import sys

from fortress_director.orchestrator.orchestrator import Orchestrator
from fortress_director.utils.logging_config import configure_logging  # type: ignore


def main() -> int:
    try:
        configure_logging()
    except Exception:
        pass
    try:
        orch = Orchestrator.build_default()
        result = orch.run_turn()
        # Basic sanity assertions so CI/logs show meaningful output
        assert isinstance(result, dict), "Turn result must be a dict"
        assert "npcs" in result, "Result missing 'npcs'"
        assert "safe_function_history" in result, "Result missing 'safe_function_history'"
        assert "room_history" in result, "Result missing 'room_history'"
        print(json.dumps({
            "ok": True,
            "npcs": len(result.get("npcs", [])),
            "safe_functions": len(result.get("safe_function_history", [])),
            "rooms": len(result.get("room_history", [])),
        }))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

