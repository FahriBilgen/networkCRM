"""Simulate 10 turns of The Mirror Archives."""

import sys
import os
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from orchestrator.orchestrator import Orchestrator


def simulate_10_turns():
    """Run 10 turns and print outputs."""
    orchestrator = Orchestrator.build_default()

    for turn in range(1, 11):
        print(f"\n=== TURN {turn} ===")

        # Run turn
        result = orchestrator.run_turn()

        # Print key outputs
        if "scene" in result:
            print(f"Scene: {result['scene'].get('description', 'N/A')[:100]}...")

        if "options" in result:
            print("Options:")
            for opt in result["options"]:
                print(f"  {opt['id']}: {opt['text']}")

        # Print scores
        state = orchestrator.state_store.snapshot()
        scores = state.get("scores", {})
        print(
            f"Scores: Logic={scores.get('logic_score', 0)}, Emotion={scores.get('emotion_score', 0)}, Corruption={scores.get('corruption', 0)}"
        )

        # Check ending
        ending = orchestrator._check_ending_conditions(state)
        if ending:
            print(f"ENDING TRIGGERED: {ending}")
            print(f"Final Scene: {result['scene'].get('description', 'N/A')}")
            break

        # Simulate player choice (random A/B/C)
        import random

        choice = random.choice(["A", "B", "C"])
        print(f"Player chooses: {choice}")

        # Run turn with choice
        result = orchestrator.run_turn(player_choice_id=choice)
        print(f"After choice - Turn: {state.get('current_turn', 1)}")

    print("\nSimulation complete!")


if __name__ == "__main__":
    simulate_10_turns()
