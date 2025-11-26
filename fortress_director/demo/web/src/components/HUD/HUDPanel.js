import { ThreatBar } from "./ThreatBar";
export class HUDPanel {
    constructor(root, store) {
        Object.defineProperty(this, "root", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "store", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "unsubscribe", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "threatBar", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: new ThreatBar()
        });
        Object.defineProperty(this, "foodEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "materialsEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "moraleEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "moodEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "visualEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "audioEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "turnEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "nextButton", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "audioCtx", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        this.root = root;
        this.store = store;
    }
    mount(onNextTurn) {
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
    destroy() {
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
    setNextTurnDisabled(disabled) {
        if (this.nextButton) {
            this.nextButton.disabled = disabled;
        }
    }
    setFinalMode(finalMode) {
        if (this.nextButton) {
            this.nextButton.classList.toggle("fd-button--hidden", finalMode);
        }
    }
    render(state) {
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
    createResourceRow(label, parent) {
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
    createAtmosphereRow(label, parent) {
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
    updateAtmosphere(descriptor) {
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
    flashAtmosphere() {
        this.root.classList.remove("fd-hud--atmosphere-pulse");
        void this.root.offsetWidth;
        this.root.classList.add("fd-hud--atmosphere-pulse");
        window.setTimeout(() => {
            this.root.classList.remove("fd-hud--atmosphere-pulse");
        }, 600);
    }
    playHoverTone() {
        if (!(window.AudioContext || window.webkitAudioContext)) {
            return;
        }
        if (!this.audioCtx) {
            const Ctor = window.AudioContext || window.webkitAudioContext;
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
