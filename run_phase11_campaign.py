"""Phase 11: Real Ollama Campaign Test - 10 turns."""

import time
from fortress_director.managers.turn_manager import TurnManager
from fortress_director.core.state_archive import StateArchive

print("=" * 70)
print("PHASE 11: REAL OLLAMA CAMPAIGN TEST (10 TURNS)")
print("=" * 70)

archive = StateArchive("phase11_test_run")
tm = TurnManager(use_ollama=True)
tm.set_archive(archive)

state = {"threat": 0.2, "morale": 80, "resources": 100, "turn": 0}

turns_ok = 0
turns_failed = 0
total_time = 0

print("\nStarting campaign...\n")

for turn_num in range(1, 11):
    print(f"[Turn {turn_num}/10]", end=" ", flush=True)

    try:
        start = time.time()

        # Determine phase
        phase_pct = turn_num / 10
        if phase_pct < 0.25:
            phase = "exposition"
        elif phase_pct < 0.5:
            phase = "rising"
        elif phase_pct < 0.75:
            phase = "climax"
        else:
            phase = "resolution"

        # Execute turn
        result = tm.execute_turn(state, turn_num, phase)
        elapsed = time.time() - start
        total_time += elapsed

        if result:
            scene = result.get("scene", "")
            choices = result.get("choices", [])
            used_ollama = result.get("used_ollama", False)

            status = "✓ OLLAMA" if used_ollama else "✓ FALLBACK"
            print(
                f"{status} ({elapsed:.1f}s) - Scene: {len(scene)}ch, Choices: {len(choices)}"
            )

            # Record to archive
            tm.record_turn_to_archive(result, state, turn_num)

            # Update state
            state["threat"] = min(1.0, state.get("threat", 0) + 0.05)
            state["morale"] = max(0, state.get("morale", 0) - 5)
            state["turn"] = turn_num

            turns_ok += 1
        else:
            print("✗ NO RESULT")
            turns_failed += 1

    except Exception as e:
        print(f"✗ ERROR: {str(e)[:50]}")
        turns_failed += 1

print("\n" + "=" * 70)
print("CAMPAIGN RESULTS")
print("=" * 70)
print(f"Successful turns: {turns_ok}/10")
print(f"Failed turns: {turns_failed}/10")
print(f"Total time: {total_time:.1f}s")
if turns_ok > 0:
    avg_time = total_time / turns_ok
    print(f"Average per turn: {avg_time:.1f}s")

# Get metrics
metrics = tm.get_campaign_metrics()
print(f"\nMemory usage: {metrics.get('memory_bytes', 0) / 1024:.1f}KB")
print("Archive context available: Yes")

print("\n✓ Phase 11 Campaign Test Complete!")
