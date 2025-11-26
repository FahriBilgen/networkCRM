import {
  fetchPlayerActions,
  fetchStatus,
  fetchThemes,
  fetchTurnTrace,
  fetchTurnTraces,
  runTurn,
  selectPlayerAction,
  updateLlmMode,
  resetForNewRun as resetSessionRequest
} from "../api/client";
import { createInitialGameState, mergeStateFromBackend } from "../state/gameState";
import type { UiStore } from "../state/uiStore";
import { uiStore } from "../state/uiStore";
import type { EventLogEntry, PlayerOption, RunTurnResponsePayload } from "../types/ui";
import { MapRenderer } from "../pixi/MapRenderer";
import { HUDPanel } from "../components/HUD/HUDPanel";
import { TurnLog } from "../components/Log/TurnLog";
import { FinalScreen, FinalSummary } from "../components/Final/FinalScreen";
import { ControlsPanel } from "./panels/ControlsPanel";
import { DebugPanel } from "./panels/DebugPanel";
import { ActionPanel } from "../components/ActionPanel";
import { buildTurnLogEntries } from "./turnLogHelpers";

const GRID_SIZE = 12;
const MAX_LOG_ENTRIES = 200;

export class UIController {
  private readonly root: HTMLElement;
  private readonly store: UiStore;
  private worldState = createInitialGameState();
  private shellEl: HTMLDivElement | null = null;
  private stageCanvasHost: HTMLDivElement | null = null;
  private collapseOverlay: HTMLDivElement | null = null;
  private narrativeEl: HTMLDivElement | null = null;
  private mapRenderer: MapRenderer | null = null;
  private hudPanel: HUDPanel | null = null;
  private turnLog: TurnLog | null = null;
  private finalScreen: FinalScreen | null = null;
  private actionPanel: ActionPanel | null = null;
  private controlsPanel: ControlsPanel | null = null;
  private debugPanel: DebugPanel | null = null;
  private unsubscribeStore: (() => void) | null = null;
  private transitionTimer: number | null = null;
  private readonly debugMode = new URLSearchParams(window.location.search).get("debug") === "1";

  constructor(root: HTMLElement, store: UiStore = uiStore) {
    this.root = root;
    this.store = store;
  }

  async bootstrap(): Promise<void> {
    const shell = document.createElement("div");
    shell.className = "fd-shell";
    this.shellEl = shell;

    const hudContainer = document.createElement("div");
    hudContainer.className = "fd-shell__hud";
    const layout = document.createElement("div");
    layout.className = "fd-layout";

    const stage = document.createElement("section");
    stage.className = "fd-stage";
    const stageTitle = document.createElement("div");
    stageTitle.className = "fd-stage__title";
    stageTitle.textContent = "Tactical Map";
    const canvasHost = document.createElement("div");
    canvasHost.className = "fd-stage__canvas";
    this.stageCanvasHost = canvasHost;
    this.collapseOverlay = document.createElement("div");
    this.collapseOverlay.className = "fd-collapse-overlay";
    this.collapseOverlay.hidden = true;
    const finalContainer = document.createElement("div");
    finalContainer.className = "fd-final-container";
    this.narrativeEl = document.createElement("div");
    this.narrativeEl.className = "fd-stage__narrative";
    this.narrativeEl.textContent = "Awaiting first turn.";
    stage.append(stageTitle, canvasHost, this.collapseOverlay, finalContainer, this.narrativeEl);

    const panels = document.createElement("div");
    panels.className = "fd-panels";
    const logPanel = document.createElement("div");
    const actionPanelNode = document.createElement("div");
    const controlsPanelNode = document.createElement("div");
    panels.append(logPanel, actionPanelNode, controlsPanelNode);

    layout.append(stage, panels);
    shell.append(hudContainer, layout);
    this.root.replaceChildren(shell);

    this.hudPanel = new HUDPanel(hudContainer, this.store);
    this.hudPanel.mount(() => {
      void this.executeTurn();
    });

    this.turnLog = new TurnLog(logPanel, this.store);
    this.turnLog.mount();

    this.controlsPanel = new ControlsPanel(controlsPanelNode, this.store);
    this.controlsPanel.mount(
      (choiceId) => {
        void this.executeTurn(choiceId);
      },
      (useStub) => {
        void this.setStubMode(useStub);
      },
      (themeId) => {
        void this.handleThemeChange(themeId);
      }
    );

    this.actionPanel = new ActionPanel(actionPanelNode, this.store);
    this.actionPanel.mount((actionId, params) => {
      void this.executePlayerAction(actionId, params);
    });

    if (this.debugMode) {
      const debugSlot = document.createElement("div");
      panels.appendChild(debugSlot);
      this.store.enableDebug();
      this.debugPanel = new DebugPanel(debugSlot, this.store);
      this.debugPanel.mount(
        (turn) => {
          void this.loadTrace(turn);
        },
        () => {
          void this.refreshTraceList();
        }
      );
      void this.refreshTraceList();
    }

    this.mapRenderer = new MapRenderer(canvasHost, { gridSize: GRID_SIZE, padding: 20 });
    await this.mapRenderer.init();
    // Try to load optional tileset and fire textures (if assets exist).
    try {
      // Use PIXI Texture factory if available in runtime
      // This is a best-effort demo enhancement; missing assets are ignored.
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { Texture } = await import("pixi.js");
      const tileTextures: any[] = [];
      for (let i = 0; i < 6; i += 1) {
        try {
          tileTextures.push(Texture.from(`/assets/tiles/tile${i}.png`));
        } catch (e) {
          // ignore missing
        }
      }
      if (tileTextures.length) {
        this.mapRenderer.setTileTextures(tileTextures);
      }
      const fireFrames: any[] = [];
      for (let i = 0; i < 4; i += 1) {
        try {
          fireFrames.push(Texture.from(`/assets/tiles/fire${i}.png`));
        } catch (e) {
          // ignore
        }
      }
      if (fireFrames.length) {
        this.mapRenderer.setFireTextures(fireFrames);
      }
    } catch (err) {
      // optional enhancement failed; continue with vector fallback
      // console.debug("Tile/fx load skipped", err);
    }
    this.finalScreen = new FinalScreen(finalContainer);
    this.finalScreen.mount();
    this.finalScreen.setReplayHandler(() => {
      void this.resetForNewRun();
    });
    this.finalScreen.mount();
    this.unsubscribeStore = this.store.subscribe((state) => {
      if (this.narrativeEl) {
        this.narrativeEl.textContent = state.narrative || "No narrative available.";
      }
    });

    await this.loadThemes();
    await this.refreshStatus();
    void this.loadPlayerActions();
  }

  destroy(): void {
    this.mapRenderer?.destroy();
    this.unsubscribeStore?.();
    this.hudPanel?.destroy();
    this.turnLog?.destroy();
    this.controlsPanel?.destroy();
    this.debugPanel?.destroy();
    this.actionPanel?.destroy();
  }

  private async executeTurn(choiceId?: string): Promise<void> {
    this.store.patch({ status: "running", error: undefined });
    this.hudPanel?.setNextTurnDisabled(true);
    this.triggerTurnPulse(false);
    try {
      const sessionId = this.store.getState().sessionId;
      const themeId = this.store.getState().themeId;
      const payload = await runTurn(choiceId, sessionId, themeId);
      this.consumeTurnPayload(payload);
    } catch (error) {
      console.error("Failed to reach backend, falling back to simulation", error);
      await this.runLocalFallback();
    } finally {
      this.hudPanel?.setNextTurnDisabled(false);
    }
  }

  private consumeTurnPayload(payload: RunTurnResponsePayload): void {
    if (payload.session_id) {
      this.store.setSessionId(payload.session_id);
    }
    if (payload.theme_id) {
      this.store.setThemeId(payload.theme_id);
    }
    this.store.setHud(payload.hud);
    this.worldState = mergeStateFromBackend(this.worldState, payload);
    this.store.setGameState(this.worldState);
    this.store.patch({
      narrative: payload.narrative,
      atmosphere: this.worldState.atmosphere,
      status: "idle",
      error: undefined,
      threatPhase: this.worldState.threat.phase,
      threatScore: this.worldState.threat.score,
      eventSeed: payload.event_seed ?? undefined,
      worldTickDelta: payload.world_tick_delta ?? undefined,
      combatSummary: payload.combat_summary ?? undefined,
      resourcesInfo: payload.resources ?? undefined,
      npcStats: payload.npcStats ?? undefined
    });
    this.mapRenderer?.update(this.worldState);
    this.mapRenderer?.applyAtmosphere(this.worldState.atmosphere, payload.atmosphere?.audio);

    const hadCombat = Boolean(payload.combat_summary && payload.combat_summary.length > 0);
    this.triggerTurnPulse(hadCombat);
    if (hadCombat) {
      this.mapRenderer?.shake();
    }
    this.updateCollapseOverlay();
    this.updateLogEntries(payload);
    if (payload.game_over) {
      this.showFinalScreen(payload);
    } else {
      this.finalScreen?.hide();
      this.hudPanel?.setFinalMode(false);
      this.shellEl?.classList.remove("fd-shell--final");
    }
    if (this.debugMode) {
      void this.refreshTraceList();
      if (payload.trace_file) {
        void this.loadTrace(payload.hud.turn);
      }
    }
  }

  private updateLogEntries(payload: RunTurnResponsePayload): void {
    const entries = buildTurnLogEntries(payload);
    const state = this.store.getState();
    const merged = [...state.eventLog, ...entries];
    this.store.setEventLog(merged.slice(-MAX_LOG_ENTRIES));
  }

  private triggerTurnPulse(combat: boolean): void {
    if (!this.shellEl) {
      return;
    }
    this.shellEl.classList.add("fd-shell--transition");
    if (combat) {
      this.shellEl.classList.add("fd-shell--shake");
      window.setTimeout(() => this.shellEl?.classList.remove("fd-shell--shake"), 400);
    }
    if (this.transitionTimer) {
      window.clearTimeout(this.transitionTimer);
    }
    this.transitionTimer = window.setTimeout(() => {
      this.shellEl?.classList.remove("fd-shell--transition");
      this.transitionTimer = null;
    }, 250);
  }

  private updateCollapseOverlay(): void {
    if (!this.collapseOverlay) {
      return;
    }
    const isCollapse = this.worldState.threat.phase === "collapse";
    this.collapseOverlay.hidden = !isCollapse;
    this.shellEl?.classList.toggle("fd-shell--collapse", isCollapse);
  }

  private showFinalScreen(payload: RunTurnResponsePayload): void {
    if (!this.finalScreen) {
      return;
    }
    const summary = this.buildFinalSummary(payload);
    this.finalScreen.show(summary);
    this.hudPanel?.setFinalMode(true);
    this.shellEl?.classList.add("fd-shell--final");
  }

  private buildFinalSummary(payload: RunTurnResponsePayload): FinalSummary {
    const finalPayload = payload.final_payload ?? undefined;
    if (!finalPayload) {
      return this.fallbackFinalSummary(payload);
    }
    const path = finalPayload.final_path;
    const narrative = finalPayload.final_narrative ?? {};
    const atmosphere = narrative.atmosphere ?? {
      mood: this.worldState.atmosphere.mood,
      visuals: this.worldState.atmosphere.visual,
      audio: this.worldState.atmosphere.audio
    };
    const closing = narrative.closing_paragraphs && narrative.closing_paragraphs.length > 0
      ? narrative.closing_paragraphs
      : [narrative.subtitle ?? path?.summary ?? "", narrative.decision_summary ?? ""].filter(Boolean);
    return {
      endingTitle: path?.title ?? "Final Sequence",
      endingSubtitle: narrative.subtitle ?? path?.summary ?? payload.event_node_description ?? "Final directive completed.",
      closingParagraphs: closing as string[],
      npcFates: narrative.npc_fates ?? finalPayload.npc_outcomes ?? [],
      structureReport: finalPayload.structure_outcomes ?? [],
      threat: finalPayload.threat_summary ?? {
        phase: this.worldState.threat.phase,
        score: this.worldState.threat.score
      },
      resources: finalPayload.resource_summary ?? {
        morale: this.worldState.resources.morale,
        resources: this.worldState.resources.materials,
        stockpiles: {
          food: this.worldState.resources.food,
          materials: this.worldState.resources.materials
        }
      },
      atmosphere: {
        mood: atmosphere.mood ?? this.worldState.atmosphere.mood,
        visuals: atmosphere.visuals ?? this.worldState.atmosphere.visual,
        audio: atmosphere.audio ?? this.worldState.atmosphere.audio
      },
      tone: path?.tone ?? "somber",
      decisionSummary: narrative.decision_summary,
      musicCue: this.resolveMusicCue(path?.id ?? "", path?.tone ?? "somber"),
      playAgainLabel: "Play Again"
    };
  }

  private fallbackFinalSummary(payload: RunTurnResponsePayload): FinalSummary {
    const npcFates = Object.values(this.worldState.npcPositions).map((npc) => {
      const alive = npc.health > 0;
      return {
        id: npc.name,
        name: npc.name ?? npc.role ?? "NPC",
        fate: alive ? "alive" : "fallen",
        color: alive ? "green" : "gray"
      };
    });
    const structures = Object.values(this.worldState.structures).map((structure) => ({
      id: structure.id,
      status: structure.status ?? (structure.integrity > 0 ? "intact" : "ruined"),
      integrity: structure.integrity
    }));
    const closing = [
      payload.event_node_description ?? "Final directive acknowledged.",
      `Morale ${this.worldState.resources.morale}%`,
      `Threat ${this.worldState.threat.score}%`
    ];
    return {
      endingTitle: payload.ending_id ?? "Final Sequence",
      endingSubtitle: payload.narrative,
      closingParagraphs: closing,
      npcFates,
      structureReport: structures,
      threat: {
        phase: this.worldState.threat.phase,
        score: this.worldState.threat.score
      },
      resources: {
        morale: this.worldState.resources.morale,
        resources: this.worldState.resources.materials,
        stockpiles: {
          food: this.worldState.resources.food,
          materials: this.worldState.resources.materials
        }
      },
      atmosphere: {
        mood: this.worldState.atmosphere.mood,
        visuals: this.worldState.atmosphere.visual,
        audio: this.worldState.atmosphere.audio
      },
      tone: payload.ending_id?.includes("victory") ? "triumphant" : "somber",
      musicCue: this.resolveMusicCue(payload.ending_id ?? "", payload.ending_id ?? "somber"),
      playAgainLabel: "Play Again",
      decisionSummary: payload.event_node_description ?? undefined
    };
  }

  private resolveMusicCue(pathId: string, tone: string): string {
    const normalized = pathId.toLowerCase();
    if (normalized.includes("victory") || tone === "triumphant" || tone === "hopeful") {
      return "victory";
    }
    if (normalized.includes("unknown") || tone.includes("eerie")) {
      return "eerie anomaly";
    }
    return "tragedy";
  }

  private async runLocalFallback(): Promise<void> {
    await new Promise((resolve) => setTimeout(resolve, 300));
    const nextTurn = this.worldState.turn + 1;
    const rotatedNpcs = Object.fromEntries(
      Object.entries(this.worldState.npcPositions).map(([id, npc], index) => [
        id,
        {
          ...npc,
          x: (npc.x + 1 + index) % GRID_SIZE,
          y: (npc.y + index) % GRID_SIZE
        }
      ])
    );
    this.worldState = {
      ...this.worldState,
      turn: nextTurn,
      resources: {
        ...this.worldState.resources,
        food: Math.max(0, this.worldState.resources.food - 1)
      },
      npcPositions: rotatedNpcs
    };
    this.store.patch({
      status: "error",
      narrative: "Backend unreachable. Showing simulation data.",
      error: "Backend unreachable."
    });
    this.store.setHud({
      ...this.store.getState().hud,
      turn: nextTurn
    });
    this.store.setGameState(this.worldState);
    this.mapRenderer?.update(this.worldState);
  }

  private async resetForNewRun(): Promise<void> {
    try {
      const payload = await resetSessionRequest(this.store.getState().themeId);
      if (payload.theme_id) {
        this.store.setThemeId(payload.theme_id);
      }
      this.store.setSessionId(payload.session_id);
      this.store.setHud(payload.hud);
      this.store.setEventLog(payload.event_log as EventLogEntry[]);
      this.store.patch({
        status: "idle",
        narrative: payload.narrative,
        error: undefined
      });
      this.worldState = mergeStateFromBackend(createInitialGameState(), {
        hud: payload.hud,
        resources: payload.resources ?? undefined,
        npc_positions: payload.npc_positions,
        structures: payload.structures,
        event_markers: payload.event_markers
      });
      this.store.setGameState(this.worldState);
      this.finalScreen?.hide();
      this.hudPanel?.setFinalMode(false);
      this.shellEl?.classList.remove("fd-shell--final");
      this.mapRenderer?.update(this.worldState);
    } catch (error) {
      console.error("Failed to reset session", error);
    }
  }

  private async loadThemes(): Promise<void> {
    try {
      const catalog = await fetchThemes();
      this.store.setThemes(catalog.themes ?? []);
      const activeId = this.store.getState().themeId;
      if (!catalog.themes?.some((theme) => theme.id === activeId) && catalog.themes && catalog.themes.length > 0) {
        this.store.setThemeId(catalog.themes[0].id);
      }
    } catch (error) {
      console.warn("Failed to load theme catalog", error);
    }
  }

  private async handleThemeChange(themeId: string): Promise<void> {
    if (themeId === this.store.getState().themeId) {
      return;
    }
    this.store.setThemeId(themeId);
    this.store.setSessionId(undefined);
    await this.resetForNewRun();
  }

  private async refreshStatus(): Promise<void> {
    try {
      const status = await fetchStatus();
      this.store.setLlmStatus({
        agents: status.llm ?? {},
        mode: status.mode === "stub" ? "stub" : "llm",
        version: status.version,
        useLlm: status.use_llm ?? status.mode !== "stub"
      });
    } catch (error) {
      console.warn("Failed to fetch LLM status", error);
    }
  }

  private async setStubMode(useStub: boolean): Promise<void> {
    this.store.setSettings({ useStubAgents: useStub });
    try {
      const status = await updateLlmMode(!useStub);
      this.store.setLlmStatus({
        agents: status.llm ?? this.store.getState().llmStatus?.agents ?? {},
        mode: status.mode === "stub" ? "stub" : "llm",
        version: status.version,
        useLlm: status.use_llm ?? !useStub
      });
    } catch (error) {
      console.error("Failed to update LLM mode", error);
      this.store.setSettings({ useStubAgents: !useStub });
    }
  }

  private async loadPlayerActions(): Promise<void> {
    try {
      const actions = await fetchPlayerActions();
      this.store.setPlayerActions(actions);
    } catch (error) {
      console.warn("Failed to fetch player actions", error);
    }
  }

  private async executePlayerAction(actionId: string, params: Record<string, string>): Promise<void> {
    try {
      const response = await selectPlayerAction(actionId, params, this.store.getState().sessionId);
      this.store.setSessionId(response.session_id);
      await this.executeTurn();
    } catch (error) {
      console.error("Failed to submit player action", error);
      this.store.patch({
        status: "error",
        error: "Unable to execute player action."
      });
    }
  }

  private async refreshTraceList(): Promise<void> {
    if (!this.debugMode) {
      return;
    }
    try {
      const traces = await fetchTurnTraces();
      this.store.setDebugTraces(traces);
    } catch (error) {
      console.warn("Failed to refresh trace list", error);
    }
  }

  private async loadTrace(turn: number): Promise<void> {
    if (!this.debugMode) {
      return;
    }
    try {
      const payload = await fetchTurnTrace(turn);
      this.store.setActiveTrace(turn, payload);
    } catch (error) {
      console.warn("Failed to load trace", error);
    }
  }
}
