import type { EventLogEntry, RunTurnResponsePayload } from "../types/ui";
import { formatCombatLog, formatWorldTickLog } from "./simulationLog.js";

export function buildTurnLogEntries(payload: RunTurnResponsePayload): EventLogEntry[] {
  const turn = payload.hud.turn;
  const entries: EventLogEntry[] = [];
  const timestamp = new Date().toISOString();
  const baseLog = payload.event_log ?? [];
  baseLog.forEach((entry, idx) => {
    entries.push({
      id: entry.id ?? `${turn}-entry-${idx}`,
      turn,
      text: entry.text,
      timestamp,
      kind: "events"
    });
  });
  if (payload.world_tick_delta) {
    const summary = formatWorldTickLog(payload.world_tick_delta);
    if (summary) {
      entries.push({
        id: `${turn}-world`,
        turn,
        text: summary,
        timestamp,
        kind: "world"
      });
    }
  }
  for (const summary of payload.combat_summary ?? []) {
    entries.push({
      id: `${turn}-combat-${summary.structure_id ?? "field"}`,
      turn,
      text: formatCombatLog(summary),
      timestamp,
      kind: "combat"
    });
  }
  if (payload.event_node_description) {
    entries.push({
      id: `${turn}-event-node`,
      turn,
      text: payload.event_node_description,
      timestamp,
      kind: "events"
    });
  }
  if (payload.executed_actions?.length) {
    const details = payload.executed_actions.map(
      (action) => `${action.function ?? "unknown"} (${action.status ?? "applied"})`
    );
    entries.push({
      id: `${turn}-functions`,
      turn,
      text: "Safe function execution report",
      timestamp,
      kind: "function",
      details
    });
  }
  return entries;
}
