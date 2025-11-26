from __future__ import annotations

import argparse

from fortress_director.core.state_store import GameState
from fortress_director.llm.runtime_mode import set_llm_enabled
from fortress_director.pipeline.turn_manager import TurnManager


def main(iterations: int) -> None:
    set_llm_enabled(False)
    manager = TurnManager()
    game_state = GameState()
    final_result = None
    for turn in range(iterations):
        result = manager.run_turn(game_state, player_choice={"id": "auto"})
        if result.is_final:
            final_result = result
            break
    if not final_result or final_result.final_payload is None:
        raise RuntimeError("Final engine did not trigger within the allotted turns.")
    payload = final_result.final_payload
    path = payload.get("final_path", {})
    narrative = payload.get("final_narrative", {})
    print("Final path:", path.get("id"), "-", path.get("title"))
    print("Final tone:", path.get("tone"))
    print("Closing paragraphs:")
    for paragraph in narrative.get("closing_paragraphs", [])[:3]:
        print(" •", paragraph)
    print("NPC fates:", len(payload.get("npc_outcomes", [])))
    print("Structures reported:", len(payload.get("structure_outcomes", [])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a lightweight end-to-end final test.")
    parser.add_argument("--iterations", type=int, default=40, help="Total turns to simulate.")
    args = parser.parse_args()
    main(args.iterations)
