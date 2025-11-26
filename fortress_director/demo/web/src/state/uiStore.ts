import { nanoid } from "../utils/id";
import { createInitialGameState } from "./gameState";
import type {
  EventLogEntry,
  HudMetrics,
  LlmStatus,
  PlayerActionDefinition,
  PlayerOption,
  ThemeSummary,
  TurnTraceSummary,
  UiSettings,
  UiState,
  UIGameState
} from "../types/ui";

type Listener = (state: UiState) => void;

const defaultHud: HudMetrics = {
  turn: 0,
  order: 55,
  morale: 60,
  resources: 72,
  glitch: 42,
  food: 0,
  avgMorale: 60,
  avgFatigue: 20
};

const DEFAULT_THEME_ID = "siege_default";

const initialState: UiState = {
  status: "idle",
  hud: defaultHud,
  sessionId: undefined,
  game: createInitialGameState(),
  atmosphere: {
    mood: "Calm vigil",
    visuals: "Lanterns halo the ramparts",
    audio: "Wind whispers over the battlements"
  },
  eventLog: [
    {
      id: nanoid(),
      turn: 0,
      text: "Awaiting first directive.",
      timestamp: new Date().toISOString()
    }
  ],
  narrative: "Prototype UI ready.",
  options: [],
  playerActions: [],
  llmStatus: {
    agents: {},
    mode: "llm",
    version: undefined,
    useLlm: true
  },
  settings: {
    useStubAgents: false
  },
  debug: {
    enabled: false,
    traces: []
  },
  threatPhase: "calm",
  threatScore: 0,
  eventSeed: undefined,
  worldTickDelta: undefined,
  combatSummary: undefined,
  resourcesInfo: undefined,
  npcStats: undefined,
  themeId: DEFAULT_THEME_ID,
  themes: []
};

export class UiStore {
  private state: UiState = initialState;
  private listeners: Set<Listener> = new Set();

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  getState(): UiState {
    return this.state;
  }

  patch(partial: Omit<Partial<UiState>, "settings"> & { settings?: Partial<UiSettings> }): void {
    const { settings: settingsPatch, ...rest } = partial;
    this.state = {
      ...this.state,
      ...rest,
      hud: rest.hud ?? this.state.hud,
      eventLog: rest.eventLog ?? this.state.eventLog,
      options: rest.options ?? this.state.options,
      debug: rest.debug ?? this.state.debug,
      llmStatus: rest.llmStatus ?? this.state.llmStatus,
      sessionId: rest.sessionId ?? this.state.sessionId,
      playerActions: rest.playerActions ?? this.state.playerActions,
      game: rest.game ?? this.state.game,
      settings: settingsPatch ? { ...this.state.settings, ...settingsPatch } : this.state.settings,
      themeId: rest.themeId ?? this.state.themeId,
      themes: rest.themes ?? this.state.themes
    };
    this.emit();
  }

  setHud(metrics: HudMetrics): void {
    this.patch({ hud: metrics });
  }

  setEventLog(entries: EventLogEntry[]): void {
    this.patch({ eventLog: entries });
  }

  appendEvent(text: string, turn: number): void {
    const entry: EventLogEntry = {
      id: nanoid(),
      text,
      turn,
      timestamp: new Date().toISOString()
    };
    this.patch({
      eventLog: [...this.state.eventLog, entry]
    });
  }

  setOptions(options: PlayerOption[]): void {
    this.patch({ options });
  }

  setLlmStatus(status: LlmStatus): void {
    this.patch({
      llmStatus: status,
      settings: { useStubAgents: !status.useLlm }
    });
  }

  setSessionId(sessionId: string | undefined): void {
    this.patch({ sessionId });
  }

  setPlayerActions(actions: PlayerActionDefinition[]): void {
    this.patch({ playerActions: actions });
  }

  setSettings(settings: Partial<UiSettings>): void {
    this.patch({ settings });
  }

  setGameState(game: UIGameState): void {
    this.patch({ game });
  }

  setThemes(themes: ThemeSummary[]): void {
    this.patch({ themes });
  }

  setThemeId(themeId: string): void {
    this.patch({ themeId });
  }

  enableDebug(): void {
    if (this.state.debug.enabled) {
      return;
    }
    this.state = {
      ...this.state,
      debug: { ...this.state.debug, enabled: true }
    };
    this.emit();
  }

  setDebugTraces(traces: TurnTraceSummary[]): void {
    this.state = {
      ...this.state,
      debug: {
        ...this.state.debug,
        traces
      }
    };
    this.emit();
  }

  setActiveTrace(turn: number, payload: unknown): void {
    this.state = {
      ...this.state,
      debug: {
        ...this.state.debug,
        active: { turn, payload }
      }
    };
    this.emit();
  }

  private emit(): void {
    for (const listener of this.listeners) {
      listener(this.state);
    }
  }
}

export const uiStore = new UiStore();
