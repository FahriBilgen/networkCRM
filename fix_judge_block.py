from pathlib import Path
path = Path("fortress_director/agents/judge_agent.py")
lines = path.read_text().splitlines()
for idx, line in enumerate(lines):
    if line.strip() == "verdict = {" and lines[idx-1].strip().startswith("# Return a small structured veto"):
        start = idx
        break
else:
    raise SystemExit("block start not found")
block = [
    "            if roll < disagreement_prob:",
    "                # Return a small structured veto to force the creativity/event",
    "                # loop to reframe",
    "                verdict = {",
    "                    \"consistent\": False,",
    "                    \"reason\": \"stochastic_repetition_veto\",",
    "                    \"penalty\": \"mild\",",
    "                    \"penalty_magnitude\": {\"morale\": -1, \"glitch\": 1},",
    "                    \"coherence\": 20,",
    "                    \"feedback\": {\"reframe_scene\": True},",
    "                }",
    "                LOGGER.info(\"Judge forced disagreement due to repetition\")",
    "                LOGGER.debug(\"Judge forced verdict: %s\", verdict)",
    "                return verdict",
]
# Replace original block (assume following lines until LOGGER.info) with new
end = start
while not lines[end].strip().startswith("LOGGER.info"):
    end += 1
lines[start-1:end+2] = block
path.write_text("\n".join(lines) + "\n")
