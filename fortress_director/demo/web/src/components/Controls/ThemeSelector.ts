import type { UiStore } from "../../state/uiStore";
import type { ThemeSummary, UiState } from "../../types/ui";

type ThemeChangeHandler = (themeId: string) => void;

export class ThemeSelector {
  private readonly root: HTMLElement;
  private readonly store: UiStore;
  private selectEl: HTMLSelectElement | null = null;
  private unsubscribe: (() => void) | null = null;
  private onChange?: ThemeChangeHandler;

  constructor(root: HTMLElement, store: UiStore) {
    this.root = root;
    this.store = store;
  }

  mount(onChange: ThemeChangeHandler): void {
    this.onChange = onChange;
    this.root.innerHTML = "";
    const label = document.createElement("label");
    label.className = "fd-input fd-theme-selector__label";
    const title = document.createElement("span");
    title.textContent = "Theme";
    const select = document.createElement("select");
    select.addEventListener("change", () => {
      if (select.value) {
        this.onChange?.(select.value);
      }
    });
    this.selectEl = select;
    label.append(title, select);
    this.root.appendChild(label);
    this.unsubscribe = this.store.subscribe((state) => this.render(state));
  }

  destroy(): void {
    if (this.selectEl) {
      this.selectEl.remove();
      this.selectEl = null;
    }
    this.unsubscribe?.();
    this.unsubscribe = null;
    this.root.innerHTML = "";
  }

  private render(state: UiState): void {
    if (!this.selectEl) {
      return;
    }
    const options = state.themes ?? [];
    const currentOptions = Array.from(this.selectEl.options).map((option) => option.value);
    const needsRefresh =
      options.length !== currentOptions.length ||
      options.some((theme, index) => currentOptions[index] !== theme.id);
    if (needsRefresh) {
      this.selectEl.innerHTML = "";
      for (const theme of options) {
        const option = document.createElement("option");
        option.value = theme.id;
        option.textContent = theme.label;
        this.selectEl.appendChild(option);
      }
    }
    if (state.themeId && this.selectEl.value !== state.themeId) {
      this.selectEl.value = state.themeId;
    }
    this.selectEl.disabled = options.length <= 1 || state.status === "running";
  }
}
