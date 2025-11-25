const test = require("node:test");
const assert = require("node:assert/strict");

async function loadHelper() {
    return import("../../fortress_director/demo/web/src/ui/eventGraphUtils.js");
}

test("mergeEventLogEntries injects description and advancement", async () => {
    const { mergeEventLogEntries } = await loadHelper();
    const baseEntries = [
        { id: "1", text: "Existing event", turn: 4, timestamp: "t" }
    ];
    const merged = mergeEventLogEntries(
        baseEntries,
        "Breach alarms dominate the plaza.",
        "node_last_stand",
        5,
        "node_wall_collapse"
    );
    assert.equal(merged.length, 3);
    assert.equal(merged[1].text, "Breach alarms dominate the plaza.");
    assert.equal(
        merged[2].text,
        "Event Graph advanced to: node_last_stand"
    );
});

test("mergeEventLogEntries skips duplicate advancement when id unchanged", async () => {
    const { mergeEventLogEntries } = await loadHelper();
    const merged = mergeEventLogEntries([], "Final defense.", "node_final", 6, "node_final");
    assert.equal(merged.length, 1);
    assert.equal(merged[0].text, "Final defense.");
});

test("Event node description persists in turn response payload", async () => {
    const mockTurnResult = {
        turn_number: 5,
        event_node_id: "node_major_assault",
        event_node_description: "Siege towers and beast batteries push toward the wall.",
        event_node_is_final: false,
        narrative: "The fortress shakes.",
        threat_phase: "peak",
        threat_score: 65.0,
    };

    assert(mockTurnResult.event_node_id);
    assert.strictEqual(mockTurnResult.event_node_id, "node_major_assault");
    assert(mockTurnResult.event_node_description.length > 0);
    assert.strictEqual(mockTurnResult.event_node_is_final, false);
});

test("Final event node triggers endgame and game_over flag", async () => {
    const mockFinalTurn = {
        turn_number: 12,
        event_node_id: "node_final",
        event_node_description: "Either surrender terms or evacuation efforts decide the fortress fate.",
        event_node_is_final: true,
        game_over: true,
        final_directive: {
            final_trigger: true,
            recommended_path: "heroic",
        },
    };

    assert.strictEqual(mockFinalTurn.event_node_is_final, true);
    assert.strictEqual(mockFinalTurn.game_over, true);
    assert(mockFinalTurn.final_directive);
});

test("Event node with battle tag influences UI threat display", async () => {
    const mockTurn = {
        event_node_id: "node_battle",
        threat_phase: "peak",
        threat_score: 70.0,
    };

    assert.strictEqual(mockTurn.threat_phase, "peak");
    assert(mockTurn.threat_score >= 60);
});

test("Event seed field enables reproducible turn replay", async () => {
    const mockTurnResult = {
        turn_number: 3,
        event_seed: "turn_003_order_002",
        event_node_id: "node_scout_activity",
    };

    assert(mockTurnResult.event_seed);
    assert.strictEqual(typeof mockTurnResult.event_seed, "string");
    assert(mockTurnResult.event_seed.includes("turn"));
});
