export function formatWorldTickLog(delta) {
    if (!delta) {
        return null;
    }
    const food = typeof delta.food_consumed === "number" ? delta.food_consumed : 0;
    const avgMorale = typeof delta.avg_morale === "number" ? delta.avg_morale : 0;
    const avgFatigue = typeof delta.avg_fatigue === "number" ? delta.avg_fatigue : 0;
    return `World Tick: ${food} food consumed, avg morale ${avgMorale}, avg fatigue ${avgFatigue}`;
}
export function formatCombatLog(entry) {
    const location = entry.structure_id ? ` near ${entry.structure_id}` : "";
    return `Skirmish${location} – attackers ${entry.attackers_casualties} vs defenders ${entry.defenders_casualties}`;
}
