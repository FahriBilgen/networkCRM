const test = require("node:test");
const assert = require("node:assert/strict");

test("groupEntriesByTurn clusters entries per turn", async () => {
  const { groupEntriesByTurn } = await import(
    "../../fortress_director/demo/web/src/components/Log/TurnLog.js"
  );
  const entries = [
    { id: "1", turn: 5, text: "A", timestamp: "t" },
    { id: "2", turn: 4, text: "B", timestamp: "t" },
    { id: "3", turn: 5, text: "C", timestamp: "t" }
  ];
  const grouped = groupEntriesByTurn(entries);
  assert.equal(grouped.size, 2);
  assert.equal(grouped.get(5).length, 2);
  assert.equal(grouped.get(4)[0].text, "B");
});
