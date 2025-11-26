import type { UiStore } from "../../state/uiStore";
import type { UiState } from "../../types/ui";
import { ThreatBar } from "./ThreatBar";

type NextTurnHandler = () => void;

export class HUDPanel {
  private readonly root: HTMLElement;
  private readonly store: UiStore;
  private unsubscribe: (() => void) | null = null;
  private threatBar = new ThreatBar();
  private foodEl: HTMLSpanElement | null = null;
  private materialsEl: HTMLSpanElement | null = null;
  private moraleEl: HTMLSpanElement | null = null;
  private moodEl: HTMLSpanElement | null = null;
  private visualEl: HTMLSpanElement | null = null;
  private audioEl: HTMLSpanElement | null = null;
  private turnEl: HTMLSpanElement | null = null;
  private nextButton: HTMLButtonElement | null = null;
  private audioCtx: AudioContext | null = null;

  constructor(root: HTMLElement, store: UiStore) {
    this.root = root;
    this.store = store;
  }

  mount(onNextTurn: NextTurnHandler): void {
    this.root.classList.add("fd-hud");
    this.root.innerHTML = "";
    const threatSection = document.createElement("div");
    threatSection.className = "fd-hud__threat-section";
    this.threatBar.mount(threatSection);

    const resources = document.createElement("div");
    resources.className = "fd-hud__resources";
    this.foodEl = this.createResourceRow("Food", resources);
    this.materialsEl = this.createResourceRow("Materials", resources);
    this.moraleEl = this.createResourceRow("Morale", resources);

    const atmosphere = document.createElement("div");
    atmosphere.className = "fd-hud__atmosphere";
    this.moodEl = this.createAtmosphereRow("Mood", atmosphere);
    this.visualEl = this.createAtmosphereRow("Visual", atmosphere);
    this.audioEl = this.createAtmosphereRow("Audio", atmosphere);

    const turnPanel = document.createElement("div");
    turnPanel.className = "fd-hud__turn";
    const turnLabel = document.createElement("span");
    turnLabel.textContent = "Turn";
    this.turnEl = document.createElement("span");
    this.turnEl.className = "fd-hud__turn-value";
    turnPanel.append(turnLabel, this.turnEl);

    this.nextButton = document.createElement("button");
    this.nextButton.type = "button";
    this.nextButton.className = "fd-button fd-button--primary";
    this.nextButton.textContent = "Next Turn";
    this.nextButton.addEventListener("click", () => {
      onNextTurn();
    });
    this.nextButton.addEventListener("pointerenter", () => {
      this.playHoverTone();
    });

    const turnWrapper = document.createElement("div");
    turnWrapper.className = "fd-hud__turn-panel";
    turnWrapper.append(turnPanel, this.nextButton);

    this.root.append(threatSection, resources, atmosphere, turnWrapper);
    this.unsubscribe = this.store.subscribe((state) => this.render(state));
  }

  destroy(): void {
    this.unsubscribe?.();
    this.unsubscribe = null;
    this.root.innerHTML = "";
    this.nextButton?.remove();
    this.nextButton = null;
    if (this.audioCtx) {
      void this.audioCtx.close();
      this.audioCtx = null;
    }
  }

  setNextTurnDisabled(disabled: boolean): void {
    if (this.nextButton) {
      this.nextButton.disabled = disabled;
    }
  }

  setFinalMode(finalMode: boolean): void {
    if (this.nextButton) {
      this.nextButton.classList.toggle("fd-button--hidden", finalMode);
    }
  }

  private render(state: UiState): void {
    const game = state.game;
    this.threatBar.update(state.threatScore ?? game.threat.score, state.threatPhase ?? game.threat.phase);
    if (this.turnEl) {
      this.turnEl.textContent = String(game.turn);
    }
    if (this.foodEl) {
      this.foodEl.textContent = `${game.resources.food}`;
    }
    if (this.materialsEl) {
      this.materialsEl.textContent = `${game.resources.materials}`;
    }
    if (this.moraleEl) {
      this.moraleEl.textContent = `${game.resources.morale}`;
      this.moraleEl.dataset.phase = (state.threatPhase ?? game.threat.phase).toLowerCase();
    }
    this.updateAtmosphere(game.atmosphere);
  }

  private createResourceRow(label: string, parent: HTMLElement): HTMLSpanElement {
    const row = document.createElement("div");
    row.className = "fd-hud__resource";
    const span = document.createElement("span");
    span.textContent = label;
    const value = document.createElement("span");
    value.className = "fd-hud__resource-value";
    value.textContent = "0";
    row.append(span, value);
    parent.appendChild(row);
    return value;
  }

  private createAtmosphereRow(label: string, parent: HTMLElement): HTMLSpanElement {
    const row = document.createElement("div");
    row.className = "fd-hud__atmosphere-row";
    const title = document.createElement("span");
    title.textContent = label;
    const value = document.createElement("span");
    value.className = "fd-hud__atmosphere-value";
    value.textContent = "--";
    row.append(title, value);
    parent.appendChild(row);
    return value;
  }

  private updateAtmosphere(descriptor: UiState["game"]["atmosphere"]): void {
    if (this.moodEl && descriptor.mood !== this.moodEl.textContent) {
      this.moodEl.textContent = descriptor.mood;
      this.flashAtmosphere();
    }
    if (this.visualEl && descriptor.visual !== this.visualEl.textContent) {
      this.visualEl.textContent = descriptor.visual;
      this.flashAtmosphere();
    }
    if (this.audioEl && descriptor.audio !== this.audioEl.textContent) {
      this.audioEl.textContent = descriptor.audio;
      this.flashAtmosphere();
    }
  }

  private flashAtmosphere(): void {
    this.root.classList.remove("fd-hud--atmosphere-pulse");
    void this.root.offsetWidth;
    this.root.classList.add("fd-hud--atmosphere-pulse");
    window.setTimeout(() => {
      this.root.classList.remove("fd-hud--atmosphere-pulse");
    }, 600);
  }

  private playHoverTone(): void {
    if (!(window.AudioContext || (window as { webkitAudioContext?: AudioContext }).webkitAudioContext)) {
      return;
    }
    if (!this.audioCtx) {
      const Ctor = window.AudioContext || (window as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      this.audioCtx = Ctor ? new Ctor() : null;
    }
    if (!this.audioCtx) {
      return;
    }
    void this.audioCtx.resume();
    const ctx = this.audioCtx;
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.type = "sine";
    oscillator.frequency.value = 540;
    gain.gain.value = 0.05;
    oscillator.connect(gain).connect(ctx.destination);
    const now = ctx.currentTime;
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.linearRampToValueAtTime(0.05, now + 0.04);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.25);
    oscillator.start(now);
    oscillator.stop(now + 0.3);
  }
}
