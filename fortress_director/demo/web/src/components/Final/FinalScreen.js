export class FinalScreen {
    constructor(root) {
        Object.defineProperty(this, "root", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: root
        });
        Object.defineProperty(this, "container", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "headerTitle", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "headerSubtitle", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "atmosphereEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "narrativeEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "npcGridEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "structureEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "graphEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "replayButton", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "shaderEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "active", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: false
        });
        Object.defineProperty(this, "replayHandler", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
    }
    setReplayHandler(handler) {
        this.replayHandler = handler;
    }
    mount() {
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
    show(payload) {
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
    hide() {
        if (this.container) {
            this.container.hidden = true;
            this.container.classList.remove("fd-final--visible");
        }
        this.active = false;
    }
    isVisible() {
        return this.active;
    }
    updateHeader(payload) {
        var _a, _b;
        if (this.headerTitle) {
            this.headerTitle.textContent = payload.endingTitle;
        }
        if (this.headerSubtitle) {
            const summary = payload.decisionSummary
                ? `${payload.endingSubtitle} • ${payload.decisionSummary}`
                : payload.endingSubtitle;
            this.headerSubtitle.textContent = summary;
        }
        (_a = this.shaderEl) === null || _a === void 0 ? void 0 : _a.setAttribute("data-tone", payload.tone);
        (_b = this.container) === null || _b === void 0 ? void 0 : _b.setAttribute("data-tone", payload.tone);
    }
    updateAtmosphere(payload) {
        if (!this.atmosphereEl) {
            return;
        }
        this.atmosphereEl.innerHTML = `
      <strong>${payload.atmosphere.mood}</strong>
      <p>${payload.atmosphere.visuals}</p>
      <p class="fd-final__audio">${payload.atmosphere.audio}</p>
    `;
    }
    renderNarrative(payload) {
        if (!this.narrativeEl) {
            return;
        }
        this.narrativeEl.innerHTML = "";
        payload.closingParagraphs.forEach((paragraph) => {
            const p = document.createElement("p");
            p.textContent = paragraph;
            this.narrativeEl.appendChild(p);
        });
    }
    renderNpcGrid(payload) {
        if (!this.npcGridEl) {
            return;
        }
        this.npcGridEl.innerHTML = "";
        payload.npcFates.forEach((npc) => {
            const cell = document.createElement("div");
            cell.className = "fd-final__npc";
            if (npc.color) {
                cell.classList.add(`fd-final__npc--${npc.color}`);
            }
            cell.innerHTML = `
        <span class="fd-final__npc-name">${npc.name}</span>
        <span class="fd-final__npc-fate">${npc.fate}</span>
      `;
            this.npcGridEl.appendChild(cell);
        });
    }
    renderStructureReport(payload) {
        if (!this.structureEl) {
            return;
        }
        this.structureEl.innerHTML = "";
        payload.structureReport.forEach((structure) => {
            const row = document.createElement("div");
            row.className = "fd-final__structure";
            row.innerHTML = `
        <span>${structure.id || "Unknown"}</span>
        <span>${structure.status}</span>
        <span>${structure.integrity || 0}%</span>
      `;
            this.structureEl.appendChild(row);
        });
    }
    renderGraphs(payload) {
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
    updateReplayButton(label) {
        if (!this.replayButton) {
            return;
        }
        this.replayButton.textContent = label || "Play Again";
    }
    createBar(label, value) {
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
    applyShaderTone(tone) {
        if (!this.shaderEl) {
            return;
        }
        this.shaderEl.dataset.tone = tone;
    }
    dispatchMusicCue(cue) {
        if (!this.container) {
            return;
        }
        const event = new CustomEvent("fd:final_music", { detail: { cue } });
        this.container.dispatchEvent(event);
    }
}
export function summarizeFinalStats(payload) {
    return {
        morale: payload.resources.morale,
        threat: typeof payload.threat.score === "number" ? payload.threat.score : 0,
        supplies: Object.values(payload.resources.stockpiles).reduce((sum, value) => sum + value, 0)
    };
}
