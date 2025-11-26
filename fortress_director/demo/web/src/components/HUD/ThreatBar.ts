type ThreatPhase = "calm" | "rising" | "peak" | "collapse" | string;

const PHASE_COLORS: Record<ThreatPhase, string> = {
  calm: "#3b82f6",
  rising: "#facc15",
  peak: "#fb923c",
  collapse: "#ef4444"
};

export class ThreatBar {
  private container: HTMLDivElement;
  private fill: HTMLDivElement;
  private phaseLabel: HTMLSpanElement;

  constructor() {
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

  mount(root: HTMLElement): void {
    root.appendChild(this.container);
  }

  update(score: number, phase: ThreatPhase): void {
    const clamped = Math.max(0, Math.min(100, Math.round(score)));
    const normalizedPhase = (phase ?? "calm").toLowerCase();
    this.fill.style.width = `${clamped}%`;
    this.fill.style.backgroundColor = threatColorForPhase(normalizedPhase);
    this.phaseLabel.textContent = normalizedPhase.toUpperCase();
    this.container.classList.toggle("fd-threat--collapse", normalizedPhase === "collapse");
  }
}

export function threatColorForPhase(phase: string): string {
  const normalized = phase?.toLowerCase() as ThreatPhase;
  return PHASE_COLORS[normalized] ?? "#64748b";
}
