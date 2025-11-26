const PHASE_COLORS = {
    calm: "#3b82f6",
    rising: "#facc15",
    peak: "#fb923c",
    collapse: "#ef4444"
};
export class ThreatBar {
    constructor() {
        Object.defineProperty(this, "container", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "fill", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "phaseLabel", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        this.container = document.createElement("div");
        this.container.className = "fd-threat";
        const label = document.createElement("span");
        label.className = "fd-threat__label";
        label.textContent = "Threat";
        this.fill = document.createElement("div");
        this.fill.className = "fd-threat__fill";
        this.phaseLabel = document.createElement("span");
        this.phaseLabel.className = "fd-threat__phase";
        this.phaseLabel.textContent = "CALM";
        this.container.append(label, this.fill, this.phaseLabel);
    }
    mount(root) {
        root.appendChild(this.container);
    }
    update(score, phase) {
        const clamped = Math.max(0, Math.min(100, Math.round(score)));
        const normalizedPhase = (phase ?? "calm").toLowerCase();
        this.fill.style.width = `${clamped}%`;
        this.fill.style.backgroundColor = threatColorForPhase(normalizedPhase);
        this.phaseLabel.textContent = normalizedPhase.toUpperCase();
        this.container.classList.toggle("fd-threat--collapse", normalizedPhase === "collapse");
    }
}
export function threatColorForPhase(phase) {
    const normalized = phase?.toLowerCase();
    return PHASE_COLORS[normalized] ?? "#64748b";
}
