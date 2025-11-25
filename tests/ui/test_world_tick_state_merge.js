const test = require("node:test");
const assert = require("node:assert/strict");

async function loadHelpers() {
    return import("../../fortress_director/demo/web/src/ui/simulationLog.js");
}

test("formatWorldTickLog summarizes consumption and averages", async () => {
    const { formatWorldTickLog } = await loadHelpers();
    const log = formatWorldTickLog({ food_consumed: 4, avg_morale: 52, avg_fatigue: 61 });
    assert.match(log, /4 food/);
    assert.match(log, /avg morale 52/);
    assert.match(log, /avg fatigue 61/);
});

test("formatCombatLog formats structure-aware summary", async () => {
    const { formatCombatLog } = await loadHelpers();
    const text = formatCombatLog({
        structure_id: "gate",
        attackers_casualties: 3,
        defenders_casualties: 5,
    });
    assert.match(text, /Skirmish near gate/);
    assert.match(text, /attackers 3/);
    assert.match(text, /defenders 5/);
});
