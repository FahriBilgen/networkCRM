import subprocess
text = subprocess.run(["git", "show", "HEAD:fortress_director/orchestrator/orchestrator.py"], capture_output=True, text=True).stdout
lines = text.splitlines()
for i in range(1040, 1100):
    print(f"{i+1:04d}: {lines[i]}")
