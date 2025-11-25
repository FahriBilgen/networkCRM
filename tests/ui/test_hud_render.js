const test = require("node:test");
const assert = require("node:assert/strict");

test("threatColorForPhase returns palette color", async () => {
  const { threatColorForPhase } = await import(
    "../../fortress_director/demo/web/src/components/HUD/ThreatBar.js"
  );
  assert.equal(threatColorForPhase("calm"), "#3b82f6");
  assert.equal(threatColorForPhase("collapse"), "#ef4444");
  assert.equal(threatColorForPhase("unknown"), "#64748b");
});
