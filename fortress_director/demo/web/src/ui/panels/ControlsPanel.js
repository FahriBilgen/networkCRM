export class ControlsPanel {
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
        Object.defineProperty(this, "button", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "statusEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "onTurn", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "onToggleStub", {
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
        Object.defineProperty(this, "optionsEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "selectedOptionId", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "llmStatusEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "stubToggle", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "suppressStubEvent", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: false
        });
        Object.defineProperty(this, "stubToggleHandler", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: () => {
                if (this.stubToggle) {
                    this.handleStubToggle(this.stubToggle.checked);
                }
            }
        });
        this.root = root;
        this.store = store;
    }
    mount(onTurn, onToggleStub) {
        this.onTurn = onTurn;
        this.onToggleStub = onToggleStub;
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
        controls.append(this.button, this.statusEl, this.llmStatusEl, toggleLabel, this.optionsEl);
        this.root.replaceChildren(title, controls);
        this.unsubscribe = this.store.subscribe((state) => this.render(state));
    }
    destroy() {
        this.button?.removeEventListener("click", () => this.handleClick());
        this.button = null;
        this.statusEl = null;
        if (this.stubToggle) {
            this.stubToggle.removeEventListener("change", this.stubToggleHandler);
        }
        this.unsubscribe?.();
    }
    handleClick() {
        if (this.store.getState().status === "running") {
            return;
        }
        this.onTurn?.(this.selectedOptionId ?? undefined);
    }
    render(state) {
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
    renderLlmStatus(state) {
        if (this.llmStatusEl) {
            const status = state.llmStatus;
            if (!status) {
                this.llmStatusEl.textContent = "LLM status: unknown";
            }
            else {
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
    handleStubToggle(useStub) {
        if (this.suppressStubEvent) {
            return;
        }
        this.onToggleStub?.(useStub);
    }
}
