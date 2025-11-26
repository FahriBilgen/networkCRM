import { nanoid } from "../utils/id";
import { createInitialGameState } from "./gameState";
const defaultHud = {
    turn: 0,
    order: 55,
    morale: 60,
    resources: 72,
    glitch: 42,
    food: 0,
    avgMorale: 60,
    avgFatigue: 20
};
const initialState = {
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
    npcStats: undefined
};
export class UiStore {
    constructor() {
        Object.defineProperty(this, "state", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: initialState
        });
        Object.defineProperty(this, "listeners", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: new Set()
        });
    }
    subscribe(listener) {
        this.listeners.add(listener);
        listener(this.state);
        return () => this.listeners.delete(listener);
    }
    getState() {
        return this.state;
    }
    patch(partial) {
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
            settings: settingsPatch ? { ...this.state.settings, ...settingsPatch } : this.state.settings
        };
        this.emit();
    }
    setHud(metrics) {
        this.patch({ hud: metrics });
    }
    setEventLog(entries) {
        this.patch({ eventLog: entries });
    }
    appendEvent(text, turn) {
        const entry = {
            id: nanoid(),
            text,
            turn,
            timestamp: new Date().toISOString()
        };
        this.patch({
            eventLog: [...this.state.eventLog, entry]
        });
    }
    setOptions(options) {
        this.patch({ options });
    }
    setLlmStatus(status) {
        this.patch({
            llmStatus: status,
            settings: { useStubAgents: !status.useLlm }
        });
    }
    setSessionId(sessionId) {
        this.patch({ sessionId });
    }
    setPlayerActions(actions) {
        this.patch({ playerActions: actions });
    }
    setSettings(settings) {
        this.patch({ settings });
    }
    setGameState(game) {
        this.patch({ game });
    }
    enableDebug() {
        if (this.state.debug.enabled) {
            return;
        }
        this.state = {
            ...this.state,
            debug: { ...this.state.debug, enabled: true }
        };
        this.emit();
    }
    setDebugTraces(traces) {
        this.state = {
            ...this.state,
            debug: {
                ...this.state.debug,
                traces
            }
        };
        this.emit();
    }
    setActiveTrace(turn, payload) {
        this.state = {
            ...this.state,
            debug: {
                ...this.state.debug,
                active: { turn, payload }
            }
        };
        this.emit();
    }
    emit() {
        for (const listener of this.listeners) {
            listener(this.state);
        }
    }
}
export const uiStore = new UiStore();
