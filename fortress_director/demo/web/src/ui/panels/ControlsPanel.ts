import type { UiState } from "../../types/ui";
import type { UiStore } from "../../state/uiStore";
import { ThemeSelector } from "../../components/Controls/ThemeSelector";

type TurnHandler = (choiceId?: string) => void;
type StubToggleHandler = (useStub: boolean) => void;
type ThemeChangeHandler = (themeId: string) => void;

export class ControlsPanel {
  private readonly root: HTMLElement;
  private readonly store: UiStore;
  private button: HTMLButtonElement | null = null;
  private statusEl: HTMLDivElement | null = null;
  private onTurn?: TurnHandler;
  private onToggleStub?: StubToggleHandler;
  private onThemeChange?: ThemeChangeHandler;
  private unsubscribe: (() => void) | null = null;
  private optionsEl: HTMLDivElement | null = null;
  private selectedOptionId: string | null = null;
  private llmStatusEl: HTMLDivElement | null = null;
  private stubToggle: HTMLInputElement | null = null;
  private themeSelector: ThemeSelector | null = null;
  private suppressStubEvent = false;
  private readonly stubToggleHandler = (): void => {
    if (this.stubToggle) {
      this.handleStubToggle(this.stubToggle.checked);
    }
  };

  constructor(root: HTMLElement, store: UiStore) {
    this.root = root;
    this.store = store;
  }

  mount(onTurn: TurnHandler, onToggleStub: StubToggleHandler, onThemeChange: ThemeChangeHandler): void {
    this.onTurn = onTurn;
    this.onToggleStub = onToggleStub;
    this.onThemeChange = onThemeChange;
    this.root.classList.add("fd-panel");
    const title = document.createElement("div");
    title.className = "fd-panel__title";
    title.textContent = "Controls";
    const controls = document.createElement("div");
    controls.className = "fd-controls";

    this.button = document.createElement("button");
    this.button.className = "fd-button";
    this.button.textContent = "End Turn";
    this.button.addEventListener("click", () => this.handleClick());

    this.statusEl = document.createElement("div");
    this.statusEl.className = "fd-status-text";
    this.statusEl.textContent = "Idle";

    this.llmStatusEl = document.createElement("div");
    this.llmStatusEl.className = "fd-llm-status";
    this.llmStatusEl.textContent = "LLM status: unknown";

    const toggleLabel = document.createElement("label");
    toggleLabel.className = "fd-toggle";
    this.stubToggle = document.createElement("input");
    this.stubToggle.type = "checkbox";
    this.stubToggle.addEventListener("change", this.stubToggleHandler);
    const toggleText = document.createElement("span");
    toggleText.textContent = "Use stub agents";
    toggleLabel.append(this.stubToggle, toggleText);

    this.optionsEl = document.createElement("div");
    this.optionsEl.className = "fd-options";

    const themeContainer = document.createElement("div");
    themeContainer.className = "fd-theme-selector";
    this.themeSelector = new ThemeSelector(themeContainer, this.store);
    this.themeSelector.mount((themeId) => {
      this.onThemeChange?.(themeId);
    });

    controls.append(this.button, this.statusEl, this.llmStatusEl, toggleLabel, themeContainer, this.optionsEl);
    this.root.replaceChildren(title, controls);
    this.unsubscribe = this.store.subscribe((state) => this.render(state));
  }

  destroy(): void {
    this.button?.removeEventListener("click", () => this.handleClick());
    this.button = null;
    this.statusEl = null;
    if (this.stubToggle) {
      this.stubToggle.removeEventListener("change", this.stubToggleHandler);
    }
    this.themeSelector?.destroy();
    this.themeSelector = null;
    this.unsubscribe?.();
  }

  private handleClick(): void {
    if (this.store.getState().status === "running") {
      return;
    }
    this.onTurn?.(this.selectedOptionId ?? undefined);
  }

  private render(state: UiState): void {
    if (this.button) {
      this.button.disabled = state.status === "running";
    }
    if (this.statusEl) {
      this.statusEl.textContent =
        state.status === "running"
          ? "Processing turn..."
          : state.status === "error"
            ? state.error ?? "Something went wrong."
            : "Idle";
    }
    this.renderLlmStatus(state);
    if (!this.optionsEl) {
      return;
    }
    this.optionsEl.innerHTML = "";
    for (const option of state.options) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "fd-option";
      if (this.selectedOptionId === option.id) {
        button.classList.add("fd-option--selected");
      }
      button.textContent = option.label;
      button.addEventListener("click", () => {
        this.selectedOptionId = option.id;
        this.render(this.store.getState());
      });
      this.optionsEl.appendChild(button);
    }
  }

  private renderLlmStatus(state: UiState): void {
    if (this.llmStatusEl) {
      const status = state.llmStatus;
      if (!status) {
        this.llmStatusEl.textContent = "LLM status: unknown";
      } else {
        const entries = Object.entries(status.agents ?? {});
        const detail = entries
          .map(([agent, health]) => {
            const symbol = health === "online" ? "🟢" : health === "offline" ? "🔴" : "🟡";
            return `${symbol} ${agent}`;
          })
          .join(" ");
        const modeLabel = status.mode === "stub" ? "Fallback mode" : "Live LLM";
        this.llmStatusEl.textContent = detail
          ? `${modeLabel} – ${detail}`
          : `${modeLabel} – probing...`;
      }
    }
    if (this.stubToggle) {
      this.suppressStubEvent = true;
      this.stubToggle.checked = state.settings.useStubAgents;
      this.suppressStubEvent = false;
    }
  }

  private handleStubToggle(useStub: boolean): void {
    if (this.suppressStubEvent) {
      return;
    }
    this.onToggleStub?.(useStub);
  }
}
