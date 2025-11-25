const test = require("node:test");
const assert = require("node:assert/strict");

test("summarizeMap reports layer counts", async () => {
  const [{ summarizeMap }, { createInitialGameState }] = await Promise.all([
    import("../../fortress_director/demo/web/src/pixi/MapRenderer.js"),
    import("../../fortress_director/demo/web/src/state/gameState.js")
  ]);
  const state = createInitialGameState();
  state.npcPositions.alpha = { x: 1, y: 1, health: 80, morale: 70, fatigue: 10 };
  state.structures.wall = { id: "wall", x: 0, y: 0, integrity: 80, maxIntegrity: 100, on_fire: false };
  state.eventMarkers.push({ id: "marker", x: 3, y: 3, severity: 2, description: "Distress" });
  const snapshot = summarizeMap(state, 12);
  assert.equal(snapshot.tileCount, 144);
  assert.equal(snapshot.npcCount, 1);
  assert.equal(snapshot.structureCount, 1);
  assert.equal(snapshot.markerCount, 1);
});
