const test = require("node:test");
const assert = require("node:assert/strict");

test("buildTurnLogEntries annotates combat and event entries", async () => {
  const { buildTurnLogEntries } = await import(
    "../../fortress_director/demo/web/src/ui/turnLogHelpers.js"
  );
  const payload = {
    hud: { turn: 7 },
    event_log: [{ text: "A" }],
    world_tick_delta: { food_consumed: 3 },
    combat_summary: [{ attackers_casualties: 1, defenders_casualties: 2, structure_id: "gate" }],
    event_node_description: "Final strike",
    executed_actions: [{ function: "deploy_scouts", status: "applied" }]
  };
  const entries = buildTurnLogEntries(payload);
  assert.equal(entries.length, 5);
  const combatEntry = entries.find((entry) => entry.kind === "combat");
  assert.ok(combatEntry.text.includes("gate"));
  const functionEntry = entries.find((entry) => entry.kind === "function");
  assert.ok(functionEntry.details[0].includes("deploy_scouts"));
});
