import { describe, expect, it } from "vitest";
import { createInitialGameState, mergeStateFromBackend } from "./gameState";
import type { GameStateMergePayload } from "./gameState";

describe("gameState merge pipeline", () => {
  it("merges npc, structure, and marker payloads", () => {
    const initial = createInitialGameState();
    const payload: GameStateMergePayload = {
      turn: 2,
      npc_positions: {
        ila: { x: 3, y: 4, health: 42, morale: 55, fatigue: 18 }
      },
      structures: {
        gate: {
          x: 5,
          y: 5,
          integrity: 72,
          max_integrity: 90,
          kind: "gatehouse",
          on_fire: true
        }
      },
      event_markers: [
        { id: "distress", x: 4, y: 8, severity: 3, description: "Distress" },
        { id: "flare", x: 1, y: 2, severity: 1, description: "Flare" }
      ],
      threat_score: 64,
      threat_phase: "peak",
      event_node_id: "node_assault",
      event_node_description: "Main assault engages the ramparts."
    };
    const next = mergeStateFromBackend(initial, payload);
    expect(next.turn).toBe(2);
    expect(next.threat.score).toBe(64);
    expect(next.threat.phase).toBe("peak");
    expect(next.npcPositions.ila.health).toBe(42);
    expect(next.structures.gate.on_fire).toBe(true);
    expect(next.eventMarkers[0].id).toBe("distress");
    expect(next.eventNode.id).toBe("node_assault");
  });

  it("retains previous data when payload omits sections", () => {
    const baselinePayload: GameStateMergePayload = {
      npc_positions: { scout: { x: 1, y: 1, health: 90 } },
      structures: { wall: { x: 2, y: 2, integrity: 80, max_integrity: 100 } }
    };
    const merged = mergeStateFromBackend(createInitialGameState(), baselinePayload);
    const followUp = mergeStateFromBackend(merged, { turn: 3 });
    expect(followUp.npcPositions.scout).toBeDefined();
    expect(followUp.structures.wall.integrity).toBe(80);
    expect(followUp.turn).toBe(3);
  });

  it("extracts combat summary strings", () => {
    const next = mergeStateFromBackend(createInitialGameState(), {
      combat_summary: [
        { attackers_casualties: 3, defenders_casualties: 1, structure_id: "gate" }
      ]
    });
    expect(next.lastCombatSummary).toContain("attackers 3");
    expect(next.lastCombatSummary).toContain("@ gate");
  });
});
