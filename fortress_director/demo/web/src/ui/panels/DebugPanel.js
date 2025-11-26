export class DebugPanel {
    constructor(root, store) {
        Object.defineProperty(this, "root", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: root
        });
        Object.defineProperty(this, "store", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "listEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "previewEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "unsubscribe", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "onSelect", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "onRefresh", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        this.store = store;
    }
    mount(onSelect, onRefresh) {
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
    destroy() {
        this.unsubscribe?.();
        this.listEl = null;
        this.previewEl = null;
    }
    render(state) {
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
        }
        else if (traces.length === 0) {
            this.previewEl.textContent = "No traces recorded yet.";
        }
        else {
            this.previewEl.textContent = "Select a trace to inspect its payload.";
        }
    }
}
