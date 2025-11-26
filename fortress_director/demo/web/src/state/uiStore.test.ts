import { describe, expect, it } from "vitest";

import { UiStore } from "./uiStore";

describe("UiStore threat telemetry", () => {
  it("stores threat and event seed data", () => {
    const store = new UiStore();
    store.patch({
      threatPhase: "peak",
      threatScore: 64.5,
      eventSeed: "enemy_assault"
    });
    const state = store.getState();
    expect(state.threatPhase).toBe("peak");
    expect(state.threatScore).toBeCloseTo(64.5);
    expect(state.eventSeed).toBe("enemy_assault");
  });
});
