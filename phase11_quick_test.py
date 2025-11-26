"""Phase 11: Quick Ollama Test - 5 turns."""

import time
from fortress_director.managers.turn_manager import TurnManager
from fortress_director.core.state_archive import StateArchive

print("\n" + "=" * 70)
print("PHASE 11: REAL OLLAMA TEST (5 TURNS)")
print("=" * 70 + "\n")

archive = StateArchive("phase11_quick_test")
tm = TurnManager(use_ollama=True)
tm.set_archive(archive)

state = {"threat": 0.2, "morale": 80, "resources": 100}

turns_ok = 0
total_time = 0

for turn_num in range(1, 6):
    print(f"[Turn {turn_num}]", end=" ", flush=True)

    try:
        start = time.time()
        result = tm.execute_turn(state, turn_num, "exposition")
        elapsed = time.time() - start
        total_time += elapsed

        if result:
            scene = result.get("scene", "")
            choices = result.get("choices", [])
            used_ollama = result.get("used_ollama", False)

            status = "OLLAMA" if used_ollama else "FALLBACK"
            print(f"✓ {status:8} {elapsed:6.1f}s Scene:{len(scene):3}ch")

            tm.record_turn_to_archive(result, state, turn_num)
            state["threat"] += 0.05
            turns_ok += 1
        else:
            print("✗ NO RESULT")

    except Exception as e:
        print(f"✗ ERROR: {str(e)[:40]}")

print("\n" + "=" * 70)
print(f"Result: {turns_ok}/5 turns OK")
print(f"Total time: {total_time:.1f}s")
if turns_ok > 0:
    print(f"Avg/turn: {total_time/turns_ok:.1f}s")
print("=" * 70 + "\n")
