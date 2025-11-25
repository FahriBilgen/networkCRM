const test = require("node:test");
const assert = require("node:assert/strict");

async function loadStateHelpers() {
  return import("../../fortress_director/demo/web/src/state/gameState.js");
}

test("mergeStateFromBackend merges npc stats and threat data", async () => {
  const { createInitialGameState, mergeStateFromBackend } = await loadStateHelpers();
  const initial = createInitialGameState();
  const merged = mergeStateFromBackend(initial, {
    turn: 3,
    npc_positions: {
      scout: { x: 2, y: 4, health: 40, morale: 55, fatigue: 12, name: "Scout" }
    },
    threat_score: 72,
    threat_phase: "peak"
  });
  assert.equal(merged.turn, 3);
  assert.equal(merged.npcPositions.scout.health, 40);
  assert.equal(merged.threat.score, 72);
  assert.equal(merged.threat.phase, "peak");
});

test("combat summary collapses to text payload", async () => {
  const { createInitialGameState, mergeStateFromBackend } = await loadStateHelpers();
  const initial = createInitialGameState();
  const merged = mergeStateFromBackend(initial, {
    combat_summary: [{ attackers_casualties: 2, defenders_casualties: 5, structure_id: "gate" }]
  });
  assert.ok(merged.lastCombatSummary);
  assert.match(merged.lastCombatSummary, /attackers 2/i);
});
