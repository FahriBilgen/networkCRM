const DEFAULT_VISIBLE_ENTRIES = 50;
export class TurnLog {
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
        Object.defineProperty(this, "listEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "loadMoreButton", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "visibleLimit", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: DEFAULT_VISIBLE_ENTRIES
        });
        Object.defineProperty(this, "unsubscribe", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "collapsed", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: new Set()
        });
        this.root = root;
        this.store = store;
    }
    mount() {
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
    destroy() {
        this.unsubscribe?.();
        this.listEl = null;
        this.root.innerHTML = "";
    }
    render(state) {
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
                }
                else {
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
    renderEntry(entry) {
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
    shouldStickToBottom() {
        if (!this.listEl) {
            return true;
        }
        const threshold = 80;
        return this.listEl.scrollHeight - (this.listEl.scrollTop + this.listEl.clientHeight) < threshold;
    }
    scrollToBottom() {
        if (!this.listEl) {
            return;
        }
        this.listEl.scrollTop = this.listEl.scrollHeight;
    }
}
export function groupEntriesByTurn(entries) {
    const grouped = new Map();
    for (const entry of entries) {
        if (!grouped.has(entry.turn)) {
            grouped.set(entry.turn, []);
        }
        grouped.get(entry.turn).push(entry);
    }
    return new Map([...grouped.entries()].sort((a, b) => a[0] - b[0]));
}
