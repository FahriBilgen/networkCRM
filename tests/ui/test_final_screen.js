const test = require("node:test");
const assert = require("node:assert/strict");

test("summarizeFinalStats mirrors payload values", async () => {
  const { summarizeFinalStats } = await import(
    "../../fortress_director/demo/web/src/components/Final/FinalScreen.js"
  );
  const summary = summarizeFinalStats({
    endingTitle: "Ashen Dawn",
    endingSubtitle: "The siege winds down.",
    closingParagraphs: ["one", "two", "three"],
    npcFates: [],
    structureReport: [],
    threat: { phase: "peak", score: 70 },
    resources: { morale: 42, resources: 10, stockpiles: { food: 5, wood: 3, ore: 2 } },
    atmosphere: { mood: "somber", visuals: "", audio: "" },
    tone: "somber",
    musicCue: "tragedy"
  });
  assert.deepEqual(summary, {
    morale: 42,
    threat: 70,
    supplies: 10
  });
});
