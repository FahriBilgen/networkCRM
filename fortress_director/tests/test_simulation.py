"""10-turn simulation test for The Mirror Archives."""

import json
import sys
import os
import random

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from orchestrator.orchestrator import Orchestrator


def run_simulation():
    """Run 10-turn simulation with random choices."""
    print("🚀 Starting Mirror Archives 10-turn simulation...\n")

    orchestrator = Orchestrator.build_default()

    for turn in range(1, 11):
        print(f"{'='*50}")
        print(f"TURN {turn}")
        print(f"{'='*50}")

        # Get current state
        state = orchestrator.state_store.snapshot()
        print(f"Current Turn: {state['turn']}")
        scores = state.get("scores", {})
        print(
            f"Scores - Logic: {scores.get('logic_score', 'N/A')}, "
            f"Emotion: {scores.get('emotion_score', 'N/A')}, "
            f"Corruption: {scores.get('corruption', 'N/A')}"
        )
        print(f"Active Layer: {state.get('active_layer', 'N/A')}")
        print()

        # Run turn
        try:
            result = orchestrator.run_turn()

            # Check if this is an ending scene
            if "WORLD_CONTEXT" in result and "scene" in result and "options" in result:
                print("🎯 ENDING REACHED!")
                print("FINAL SCENE:")
                print(result.get("scene", {}).get("description", "N/A"))
                return

            print("WORLD CONTEXT:")
            world = result.get("world", {})
            if isinstance(world, dict):
                print(f"Atmosphere: {world.get('atmosphere', 'N/A')}")
                print(f"Sensory Details: {world.get('sensory_details', 'N/A')}")
            else:
                print(world)
            print()

            print("SCENE:")
            event = result.get("event", {})
            if isinstance(event, dict):
                scene = event.get("scene", {})
                if isinstance(scene, dict):
                    print(f"Title: {scene.get('title', 'N/A')}")
                    print(f"Description: {scene.get('description', 'N/A')}")
                else:
                    print(f"Description: {scene}")
            else:
                print(event)
            print()

            options = result.get("options", [])
            if options:
                print("OPTIONS:")
                for i, option in enumerate(options, 1):
                    print(f"{i}. {option}")
                print()

                # Make random choice
                choice_idx = random.randint(0, len(options) - 1)
                choice = options[choice_idx]
                print(f"🤖 AI chooses: {choice_idx + 1}. {choice}")
                print()

                # Apply choice
                choice_result = orchestrator.apply_choice(choice_idx)
                print("CHOICE RESULT:")
                print(json.dumps(choice_result, indent=2))
                print()

            # Show speakers if available
            speakers = result.get("speakers", [])
            if speakers:
                print("CHARACTER REACTIONS:")
                for speaker in speakers:
                    if isinstance(speaker, dict):
                        print(
                            f"{speaker.get('id', 'Unknown')}: {speaker.get('line', 'N/A')}"
                        )
                print()

            # Show judge result if available
            judge = result.get("judge", {})
            if judge:
                print("JUDGE VALIDATION:")
                print(f"Tier: {judge.get('tier', 'N/A')}")
                print(f"Explanation: {judge.get('explanation', 'N/A')}")
                print()

            # Check for ending
            if result.get("ending_reached", False):
                print("🎯 ENDING REACHED!")
                return

        except Exception as e:
            print(f"❌ Error in turn {turn}: {e}")
            return

    print("\n🏁 Simulation complete!")


if __name__ == "__main__":
    run_simulation()
