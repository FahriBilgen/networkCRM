import type { UiState } from "../../types/ui";
import type { UiStore } from "../../state/uiStore";

type TraceSelectHandler = (turn: number) => void;
type TraceRefreshHandler = () => void;

export class DebugPanel {
  private readonly store: UiStore;
  private listEl: HTMLDivElement | null = null;
  private previewEl: HTMLPreElement | null = null;
  private unsubscribe: (() => void) | null = null;
  private onSelect?: TraceSelectHandler;
  private onRefresh?: TraceRefreshHandler;

  constructor(private root: HTMLElement, store: UiStore) {
    this.store = store;
  }

  mount(onSelect: TraceSelectHandler, onRefresh: TraceRefreshHandler): void {
    this.onSelect = onSelect;
    this.onRefresh = onRefresh;
    this.root.classList.add("fd-panel", "fd-debug-panel");
    const title = document.createElement("div");
    title.className = "fd-panel__title";
    title.textContent = "Debug Traces";

    const refreshButton = document.createElement("button");
    refreshButton.className = "fd-button";
    refreshButton.textContent = "Reload Traces";
    refreshButton.addEventListener("click", () => this.onRefresh?.());

    this.listEl = document.createElement("div");
    this.listEl.className = "fd-debug-list";

    this.previewEl = document.createElement("pre");
    this.previewEl.className = "fd-log__entry";
    this.previewEl.style.whiteSpace = "pre-wrap";

    this.root.replaceChildren(title, refreshButton, this.listEl, this.previewEl);
    this.unsubscribe = this.store.subscribe((state) => this.render(state));
  }

  destroy(): void {
    this.unsubscribe?.();
    this.listEl = null;
    this.previewEl = null;
  }

  private render(state: UiState): void {
    if (!this.listEl || !this.previewEl) {
      return;
    }
    const { traces, active } = state.debug;
    this.listEl.innerHTML = "";
    for (const trace of traces) {
      const entry = document.createElement("button");
      entry.type = "button";
      entry.className = "fd-debug-entry";
      if (active?.turn === trace.turn) {
        entry.classList.add("fd-debug-entry--active");
      }
      const label = trace.modified_ts
        ? `Turn ${trace.turn} - ${new Date(trace.modified_ts * 1000).toLocaleTimeString()}`
        : `Turn ${trace.turn}`;
      entry.textContent = label;
      entry.addEventListener("click", () => this.onSelect?.(trace.turn));
      this.listEl.appendChild(entry);
    }
    if (active?.payload) {
      this.previewEl.textContent = JSON.stringify(active.payload, null, 2);
    } else if (traces.length === 0) {
      this.previewEl.textContent = "No traces recorded yet.";
    } else {
      this.previewEl.textContent = "Select a trace to inspect its payload.";
    }
  }
}
