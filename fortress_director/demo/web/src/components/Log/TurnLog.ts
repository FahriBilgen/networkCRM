import type { UiStore } from "../../state/uiStore";
import type { EventLogEntry, UiState } from "../../types/ui";

const DEFAULT_VISIBLE_ENTRIES = 50;

export class TurnLog {
  private readonly root: HTMLElement;
  private readonly store: UiStore;
  private listEl: HTMLDivElement | null = null;
  private loadMoreButton: HTMLButtonElement | null = null;
  private visibleLimit = DEFAULT_VISIBLE_ENTRIES;
  private unsubscribe: (() => void) | null = null;
  private collapsed: Set<number> = new Set();

  constructor(root: HTMLElement, store: UiStore) {
    this.root = root;
    this.store = store;
  }

  mount(): void {
    this.root.classList.add("fd-log-panel");
    const header = document.createElement("div");
    header.className = "fd-panel__title";
    header.textContent = "Turn Log";
    this.listEl = document.createElement("div");
    this.listEl.className = "fd-log-panel__list";
    this.loadMoreButton = document.createElement("button");
    this.loadMoreButton.type = "button";
    this.loadMoreButton.className = "fd-button fd-button--ghost";
    this.loadMoreButton.textContent = "Load more";
    this.loadMoreButton.addEventListener("click", () => {
      this.visibleLimit += 25;
      this.render(this.store.getState());
    });
    this.root.replaceChildren(header, this.loadMoreButton, this.listEl);
    this.unsubscribe = this.store.subscribe((state) => this.render(state));
  }

  destroy(): void {
    this.unsubscribe?.();
    this.listEl = null;
    this.root.innerHTML = "";
  }

  private render(state: UiState): void {
    if (!this.listEl) {
      return;
    }
    const entries = state.eventLog.slice(-this.visibleLimit);
    this.loadMoreButton?.classList.toggle("fd-button--hidden", state.eventLog.length <= this.visibleLimit);
    const grouped = groupEntriesByTurn(entries);
    const shouldStick = this.shouldStickToBottom();
    this.listEl.innerHTML = "";
    for (const [turn, turnEntries] of grouped) {
      const section = document.createElement("div");
      section.className = "fd-log-panel__section";
      const header = document.createElement("button");
      header.type = "button";
      header.className = "fd-log-panel__section-header";
      header.textContent = `Turn ${turn}`;
      const content = document.createElement("div");
      content.className = "fd-log-panel__section-content";
      const collapsed = this.collapsed.has(turn);
      content.hidden = collapsed;
      header.addEventListener("click", () => {
        if (content.hidden) {
          content.hidden = false;
          this.collapsed.delete(turn);
        } else {
          content.hidden = true;
          this.collapsed.add(turn);
        }
      });
      for (const entry of turnEntries) {
        const row = this.renderEntry(entry);
        content.appendChild(row);
      }
      section.append(header, content);
      this.listEl.appendChild(section);
    }
    if (shouldStick) {
      this.scrollToBottom();
    }
  }

  private renderEntry(entry: EventLogEntry): HTMLDivElement {
    const row = document.createElement("div");
    row.className = "fd-log-panel__entry";
    if (entry.kind) {
      row.dataset.kind = entry.kind;
    }
    const text = document.createElement("div");
    text.textContent = entry.text;
    row.appendChild(text);
    if (entry.details?.length) {
      const detailList = document.createElement("ul");
      detailList.className = "fd-log-panel__details";
      for (const detail of entry.details) {
        const li = document.createElement("li");
        li.textContent = detail;
        detailList.appendChild(li);
      }
      row.appendChild(detailList);
    }
    return row;
  }

  private shouldStickToBottom(): boolean {
    if (!this.listEl) {
      return true;
    }
    const threshold = 80;
    return this.listEl.scrollHeight - (this.listEl.scrollTop + this.listEl.clientHeight) < threshold;
  }

  private scrollToBottom(): void {
    if (!this.listEl) {
      return;
    }
    this.listEl.scrollTop = this.listEl.scrollHeight;
  }
}

export function groupEntriesByTurn(entries: EventLogEntry[]): Map<number, EventLogEntry[]> {
  const grouped = new Map<number, EventLogEntry[]>();
  for (const entry of entries) {
    if (!grouped.has(entry.turn)) {
      grouped.set(entry.turn, []);
    }
    grouped.get(entry.turn)!.push(entry);
  }
  return new Map([...grouped.entries()].sort((a, b) => a[0] - b[0]));
}
