#!/usr/bin/env python3
"""Script to run full Fortress Director game until final outcome."""

import sys
import os
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from fortress_director.orchestrator.orchestrator import Orchestrator
from fortress_director.utils.logging_config import configure_logging


def run_full_game():
    """Run the game from start to finish until win/loss."""
    print("Fortress Director - Full Game Run")
    print("=" * 60)

    # Setup logging
    log_path = Path("full_game.log")
    configure_logging(
        console_level=logging.INFO,
        file_level=logging.DEBUG,
        log_path=log_path,
        force=True,
    )
    print(f" Logs will be saved to: {log_path}")

    orchestrator = Orchestrator.build_default()

    turn_count = 0
    max_turns = 5
    player_choice_id = None
    outcomes = []

    while turn_count < max_turns:
        try:
            print(f"\n Turn {turn_count + 1}")
            print("-" * 40)

            # Run the turn
            result = orchestrator.run_turn(player_choice_id=player_choice_id)

            # Record outcome
            turn_outcome = {
                "turn": turn_count + 1,
                "scene": result.get("scene", "")[:100],
                "player_choice": result.get("player_choice", {}).get("text", ""),
                "win_loss": result.get("win_loss", {}),
                "metrics": result.get("metrics_after", {}),
            }
            outcomes.append(turn_outcome)

            # Print summary
            print(f" Scene: {turn_outcome['scene']}...")
            print(f" Choice: {turn_outcome['player_choice']}")
            print(
                f" Metrics: Morale={turn_outcome['metrics'].get('morale', 0)}, Order={turn_outcome['metrics'].get('order', 0)}"
            )
            print(f" Status: {turn_outcome['win_loss'].get('status', 'ongoing')}")

            # Check win/loss
            win_loss = result.get("win_loss", {})
            if win_loss.get("status") != "ongoing":
                print(f"\n Game Ended: {win_loss.get('reason', 'unknown')}")
                print(f" {win_loss.get('description', '')}")
                break

            # Choose next option (first available)
            options = result.get("options", [])
            if options:
                player_choice_id = options[0].get("id")
            else:
                print("No options available, ending game.")
                break

            turn_count += 1

        except Exception as e:
            print(f" Error in turn {turn_count + 1}: {e}")
            break

    # Save outcomes
    output_file = Path("full_game_outcomes.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(outcomes, f, indent=2, ensure_ascii=False)
    print(f"\n Outcomes saved to: {output_file}")
    print(f" Logs saved to: {log_path}")

    return outcomes


if __name__ == "__main__":
    run_full_game()
