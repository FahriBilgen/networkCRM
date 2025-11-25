const test = require("node:test");
const assert = require("node:assert/strict");

test("resolveAtmosphereState toggles overlay and filters", async () => {
  const { resolveAtmosphereState } = await import(
    "../../fortress_director/demo/web/src/pixi/AtmosphereEffects.js"
  );
  const grim = resolveAtmosphereState("grim", "fire");
  assert.equal(grim.overlay, true);
  assert.equal(grim.fire, true);

  const hopeful = resolveAtmosphereState("hopeful", "wind");
  assert.equal(hopeful.warm, true);
  assert.equal(hopeful.wind, true);
});
