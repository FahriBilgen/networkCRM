export interface FinalNpcFate {
  id?: string;
  name: string;
  fate: string;
  color?: string;
}

export interface FinalStructureOutcome {
  id?: string;
  status: string;
  integrity?: number;
}

export interface FinalThreatSummary {
  phase: string;
  score?: number | null;
}

export interface FinalResourceSummary {
  morale: number;
  resources: number;
  stockpiles: Record<string, number>;
}

export interface FinalSummary {
  endingTitle: string;
  endingSubtitle: string;
  closingParagraphs: string[];
  npcFates: FinalNpcFate[];
  structureReport: FinalStructureOutcome[];
  threat: FinalThreatSummary;
  resources: FinalResourceSummary;
  atmosphere: {
    mood: string;
    visuals: string;
    audio: string;
  };
  tone: string;
  decisionSummary?: string;
  musicCue: string;
  playAgainLabel?: string;
}

export class FinalScreen {
  private readonly root: HTMLElement;
  private container: HTMLDivElement | null = null;
  private headerTitle: HTMLHeadingElement | null = null;
  private headerSubtitle: HTMLParagraphElement | null = null;
  private atmosphereEl: HTMLDivElement | null = null;
  private narrativeEl: HTMLDivElement | null = null;
  private npcGridEl: HTMLDivElement | null = null;
  private structureEl: HTMLDivElement | null = null;
  private graphEl: HTMLDivElement | null = null;
  private replayButton: HTMLButtonElement | null = null;
  private shaderEl: HTMLDivElement | null = null;
  private active = false;
  private replayHandler: (() => void) | null = null;

  constructor(root: HTMLElement) {
    this.root = root;
  }

  setReplayHandler(handler: () => void): void {
    this.replayHandler = handler;
  }

  mount(): void {
    this.container = document.createElement("div");
    this.container.className = "fd-final";

    this.shaderEl = document.createElement("div");
    this.shaderEl.className = "fd-final__shader";
    this.container.appendChild(this.shaderEl);

    const panel = document.createElement("div");
    panel.className = "fd-final__panel";

    const header = document.createElement("div");
    header.className = "fd-final__header";
    this.headerTitle = document.createElement("h1");
    this.headerSubtitle = document.createElement("p");
    this.atmosphereEl = document.createElement("div");
    this.atmosphereEl.className = "fd-final__atmosphere";
    header.append(this.headerTitle, this.headerSubtitle, this.atmosphereEl);

    this.narrativeEl = document.createElement("div");
    this.narrativeEl.className = "fd-final__narrative";

    const grids = document.createElement("div");
    grids.className = "fd-final__details";

    this.npcGridEl = document.createElement("div");
    this.npcGridEl.className = "fd-final__npc-grid";
    this.structureEl = document.createElement("div");
    this.structureEl.className = "fd-final__structures";
    grids.append(this.npcGridEl, this.structureEl);

    this.graphEl = document.createElement("div");
    this.graphEl.className = "fd-final__graphs";

    this.replayButton = document.createElement("button");
    this.replayButton.className = "fd-final__replay";
    this.replayButton.addEventListener("click", () => {
      if (this.replayHandler) {
        this.replayHandler();
      }
    });

    panel.append(header, this.narrativeEl, grids, this.graphEl, this.replayButton);
    this.container.appendChild(panel);
    this.container.hidden = true;
    this.root.appendChild(this.container);
  }

  show(payload: FinalSummary): void {
    if (!this.container) {
      this.mount();
    }
    if (!this.container) {
      return;
    }
    this.container.hidden = false;
    this.container.classList.add("fd-final--visible");
    this.container.dataset.tone = payload.tone;
    this.container.dataset.musicCue = payload.musicCue;
    this.applyShaderTone(payload.tone);
    this.updateHeader(payload);
    this.renderNarrative(payload);
    this.renderNpcGrid(payload);
    this.renderStructureReport(payload);
    this.renderGraphs(payload);
    this.updateAtmosphere(payload);
    this.updateReplayButton(payload.playAgainLabel);
    this.active = true;
    this.dispatchMusicCue(payload.musicCue);
  }

  hide(): void {
    if (this.container) {
      this.container.hidden = true;
      this.container.classList.remove("fd-final--visible");
    }
    this.active = false;
  }

  isVisible(): boolean {
    return this.active;
  }

  private updateHeader(payload: FinalSummary): void {
    if (this.headerTitle) {
      this.headerTitle.textContent = payload.endingTitle;
    }
    if (this.headerSubtitle) {
      const summary = payload.decisionSummary
        ? `${payload.endingSubtitle} • ${payload.decisionSummary}`
        : payload.endingSubtitle;
      this.headerSubtitle.textContent = summary;
    }
  }

  private updateAtmosphere(payload: FinalSummary): void {
    if (!this.atmosphereEl) {
      return;
    }
    this.atmosphereEl.innerHTML = `
      <strong>${payload.atmosphere.mood}</strong>
      <p>${payload.atmosphere.visuals}</p>
      <p class="fd-final__audio">${payload.atmosphere.audio}</p>
    `;
  }

  private renderNarrative(payload: FinalSummary): void {
    if (!this.narrativeEl) {
      return;
    }
    this.narrativeEl.innerHTML = "";
    payload.closingParagraphs.forEach((paragraph) => {
      const p = document.createElement("p");
      p.textContent = paragraph;
      this.narrativeEl?.appendChild(p);
    });
  }

  private renderNpcGrid(payload: FinalSummary): void {
    if (!this.npcGridEl) {
      return;
    }
    this.npcGridEl.innerHTML = "";
    payload.npcFates.forEach((npc) => {
      const cell = document.createElement("div");
      cell.className = "fd-final__npc";
      const colorClass = npc.color ? `fd-final__npc--${npc.color}` : "";
      if (colorClass) {
        cell.classList.add(colorClass);
      }
      cell.innerHTML = `<span class="fd-final__npc-name">${npc.name}</span><span class="fd-final__npc-fate">${npc.fate}</span>`;
      this.npcGridEl?.appendChild(cell);
    });
  }

  private renderStructureReport(payload: FinalSummary): void {
    if (!this.structureEl) {
      return;
    }
    this.structureEl.innerHTML = "";
    payload.structureReport.forEach((structure) => {
      const row = document.createElement("div");
      row.className = "fd-final__structure";
      row.innerHTML = `
        <span>${structure.id ?? "Unknown"}</span>
        <span>${structure.status}</span>
        <span>${structure.integrity ?? 0}%</span>
      `;
      this.structureEl?.appendChild(row);
    });
  }

  private renderGraphs(payload: FinalSummary): void {
    if (!this.graphEl) {
      return;
    }
    this.graphEl.innerHTML = "";
    const moraleBar = this.createBar("Morale", payload.resources.morale);
    const threatScore = typeof payload.threat.score === "number" ? payload.threat.score : 0;
    const threatBar = this.createBar(`Threat (${payload.threat.phase})`, threatScore);
    const stockpileTotal = Object.values(payload.resources.stockpiles).reduce((sum, value) => sum + value, 0);
    const stockpileBar = this.createBar("Supplies", stockpileTotal);
    this.graphEl.append(moraleBar, threatBar, stockpileBar);
  }

  private updateReplayButton(label?: string): void {
    if (!this.replayButton) {
      return;
    }
    this.replayButton.textContent = label || "Play Again";
  }

  private createBar(label: string, value: number): HTMLDivElement {
    const wrapper = document.createElement("div");
    wrapper.className = "fd-final__graph-bar";
    const title = document.createElement("span");
    title.textContent = label;
    const bar = document.createElement("div");
    bar.className = "fd-final__graph-meter";
    const normalized = Math.max(0, Math.min(100, Math.round(value)));
    bar.style.setProperty("--fd-final-meter", `${normalized}%`);
    bar.textContent = `${normalized}%`;
    wrapper.append(title, bar);
    return wrapper;
  }

  private applyShaderTone(tone: string): void {
    if (!this.shaderEl) {
      return;
    }
    this.shaderEl.dataset.tone = tone;
  }

  private dispatchMusicCue(cue: string): void {
    if (!this.container) {
      return;
    }
    const event = new CustomEvent("fd:final_music", { detail: { cue } });
    this.container.dispatchEvent(event);
  }
}

export function summarizeFinalStats(payload: FinalSummary): Record<string, number> {
  return {
    morale: payload.resources.morale,
    threat: typeof payload.threat.score === "number" ? payload.threat.score : 0,
    supplies: Object.values(payload.resources.stockpiles).reduce((sum, value) => sum + value, 0),
  };
}
