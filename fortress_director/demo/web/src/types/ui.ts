export interface UIGameState {
  turn: number;
  resources: {
    food: number;
    materials: number;
    morale: number;
  };
  threat: {
    score: number;
    phase: string;
  };
  npcPositions: Record<
    string,
    {
      x: number;
      y: number;
      health: number;
      morale: number;
      fatigue: number;
      name?: string;
      role?: string;
      hostile?: boolean;
    }
  >;
  structures: Record<
    string,
    {
      id: string;
      x: number;
      y: number;
      integrity: number;
      maxIntegrity: number;
      on_fire: boolean;
      kind?: string;
      status?: string;
    }
  >;
  eventMarkers: Array<{
    id: string;
    x: number;
    y: number;
    severity: number;
    description: string;
    entity_type?: string;
  }>;
  lastCombatSummary: string | null;
  atmosphere: {
    mood: string;
    visual: string;
    audio: string;
  };
  eventNode: {
    id: string;
    description: string;
  };
}

export interface HudMetrics {
  turn: number;
  order: number;
  morale: number;
  resources: number;
  glitch: number;
  food: number;
  avgMorale: number;
  avgFatigue: number;
}

export interface EventLogEntry {
  id: string;
  turn: number;
  text: string;
  timestamp: string;
  kind?: "combat" | "morale" | "structures" | "events" | "world" | "function";
  details?: string[];
}

export interface PlayerOption {
  id: string;
  label: string;
  description?: string;
  type?: string;
}

export interface AtmosphereDescriptor {
  mood?: string;
  visuals?: string;
  audio?: string;
}

export interface BackendStatusPayload {
  llm: Record<string, string>;
  version: string;
  mode?: string;
  use_llm?: boolean;
}

export interface LlmStatus {
  agents: Record<string, string>;
  mode: "llm" | "stub";
  version?: string;
  useLlm: boolean;
}

export interface UiSettings {
  useStubAgents: boolean;
}

export interface PlayerActionDefinition {
  id: string;
  label: string;
  requires: string[];
  safe_function: string;
  args_map: Record<string, unknown>;
}

export interface PlayerActionContext {
  player_intent: string;
  required_calls: Array<{
    function: string;
    args: Record<string, unknown>;
  }>;
}

export interface ThemeSummary {
  id: string;
  label: string;
  description: string;
}

export interface ThemeListResponsePayload {
  themes: ThemeSummary[];
}

export interface UiState {
  status: "idle" | "running" | "error";
  hud: HudMetrics;
  eventLog: EventLogEntry[];
  narrative: string;
  options: PlayerOption[];
  atmosphere?: AtmosphereDescriptor;
  error?: string;
  llmStatus?: LlmStatus;
  sessionId?: string;
  playerActions: PlayerActionDefinition[];
  settings: UiSettings;
  debug: DebugState;
  threatPhase?: string;
  threatScore?: number;
  eventSeed?: string;
  worldTickDelta?: WorldTickDeltaPayload | Record<string, unknown>;
  combatSummary?: CombatSummaryEntry[];
  resourcesInfo?: ResourceSnapshot;
  npcStats?: NpcStats;
  game: UIGameState;
  themeId: string;
  themes: ThemeSummary[];
}

export interface WorldTickDeltaPayload {
  food_consumed?: number;
  avg_fatigue?: number;
  avg_morale?: number;
  events?: string[];
}

export interface CombatSummaryEntry {
  function?: string;
  attackers_casualties: number;
  defenders_casualties: number;
  structure_id?: string;
}

export interface ResourceSnapshot {
  food: number;
  world_resources: number;
  morale?: number;
}

export interface NpcStats {
  avg_morale: number;
  avg_fatigue: number;
}

export interface BackendGridCell {
  id: string;
  x: number;
  y: number;
  entityType: string;
  label?: string;
  hostile?: boolean;
}

// Lightweight GridEntity used by the GridRenderer visuals.
export interface GridEntity {
  id?: string;
  x: number;
  y: number;
  entityType: string;
  color?: number;
  integrityRatio?: number; // 0.0 - 1.0 for structures
  severity?: number; // for markers
}

export interface BackendEventLogEntry {
  id?: string;
  turn?: number;
  text: string;
}

export interface StateDeltaPayload {
  turn_advanced?: boolean;
  resource_delta?: number;
  stability_delta?: number;
  log_entries?: string[];
  npc_positions?: Record<string, BackendNpcPosition>;
  structures?: Record<string, BackendStructureDefinition>;
  event_markers?: BackendEventMarkerDefinition[];
  metrics?: Record<string, number>;
}

export interface BackendNpcPosition {
  x: number;
  y: number;
  name?: string;
  role?: string;
  hostile?: boolean;
  health?: number;
  morale?: number;
  fatigue?: number;
}

export interface BackendStructureDefinition {
  x: number;
  y: number;
  kind?: string;
  integrity: number;
  max_integrity: number;
  status?: string;
  on_fire?: boolean;
  id?: string;
}

export interface BackendEventMarkerDefinition {
  id: string;
  x: number;
  y: number;
  severity: number;
  description?: string;
  entity_type?: string;
}

export interface EventNodePayload {
  id: string;
  description: string;
}

export interface ThreatTelemetry {
  score: number;
  phase: string;
}

export interface FinalNpcOutcome {
  id?: string;
  name?: string;
  fate: string;
  color?: string;
}

export interface FinalStructureOutcome {
  id?: string;
  status: string;
  integrity?: number;
}

export interface FinalNarrativeBlock {
  title: string;
  subtitle?: string;
  closing_paragraphs?: string[];
  npc_fates?: FinalNpcOutcome[];
  atmosphere?: AtmosphereDescriptor & {
    visuals?: string;
    audio?: string;
    mood?: string;
  };
  decision_summary?: string;
}

export interface FinalPayload {
  final_path: {
    id: string;
    title: string;
    tone: string;
    summary: string;
  };
  npc_outcomes: FinalNpcOutcome[];
  structure_outcomes: FinalStructureOutcome[];
  resource_summary: ResourceSnapshot;
  threat_summary: {
    phase: string;
    score?: number | null;
  };
  final_actions: Record<string, unknown>[];
  final_narrative: FinalNarrativeBlock;
}

export interface RunTurnResponsePayload {
  narrative: string;
  ui_events: { speaker: string; line: string }[];
  state_delta: StateDeltaPayload;
  player_options: Record<string, unknown>[];
  options?: Record<string, unknown>[]; // legacy compatibility
  hud: HudMetrics;
  grid: BackendGridCell[];
  event_log: BackendEventLogEntry[];
  executed_actions: Record<string, unknown>[];
  turn_number: number;
  game_over: boolean;
  ending_id?: string | null;
  atmosphere?: AtmosphereDescriptor;
  trace_file?: string;
  session_id: string;
  player_action_context?: PlayerActionContext | null;
  threat_score: number;
  threat_phase: string;
  event_seed?: string;
  event_node_id?: string | null;
  event_node_description?: string | null;
  event_node_is_final?: boolean;
  world_tick_delta?: WorldTickDeltaPayload | null;
  combat_summary?: CombatSummaryEntry[] | null;
  resources?: ResourceSnapshot | null;
  npcStats?: NpcStats | null;
  npc_positions?: Record<string, BackendNpcPosition>;
  structures?: Record<string, BackendStructureDefinition>;
  event_markers?: BackendEventMarkerDefinition[];
  event_node?: EventNodePayload | null;
  threat?: ThreatTelemetry | null;
  final_payload?: FinalPayload | null;
  theme_id: string;
}

export interface SelectActionResponsePayload {
  session_id: string;
  player_action_context: PlayerActionContext;
}

export interface ResetSessionResponsePayload {
  session_id: string;
  narrative: string;
  hud: HudMetrics;
  grid: BackendGridCell[];
  event_log: BackendEventLogEntry[];
  npc_stats: NpcStats | null;
  npc_positions: Record<string, BackendNpcPosition>;
  structures: Record<string, BackendStructureDefinition>;
  event_markers: BackendEventMarkerDefinition[];
  resources: ResourceSnapshot | null;
  theme_id: string;
}

export interface TurnTraceSummary {
  turn: number;
  file: string;
  modified_ts?: number;
}

export interface DebugState {
  enabled: boolean;
  traces: TurnTraceSummary[];
  active?: {
    turn: number;
    payload: unknown;
  };
}
