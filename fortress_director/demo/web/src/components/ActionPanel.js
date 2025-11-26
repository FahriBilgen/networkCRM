export class ActionPanel {
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
        Object.defineProperty(this, "onSubmit", {
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
        Object.defineProperty(this, "selectEl", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "inputsContainer", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "submitButton", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "selectedActionId", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        this.root = root;
        this.store = store;
    }
    mount(onSubmit) {
        this.onSubmit = onSubmit;
        this.root.classList.add("fd-panel");
        const title = document.createElement("div");
        title.className = "fd-panel__title";
        title.textContent = "Player Actions";
        const container = document.createElement("div");
        container.className = "fd-action-panel";
        this.selectEl = document.createElement("select");
        this.selectEl.className = "fd-action-panel__select";
        this.selectEl.addEventListener("change", () => this.handleSelectChange());
        this.inputsContainer = document.createElement("div");
        this.inputsContainer.className = "fd-action-panel__inputs";
        this.submitButton = document.createElement("button");
        this.submitButton.type = "button";
        this.submitButton.className = "fd-button";
        this.submitButton.textContent = "Execute Action";
        this.submitButton.addEventListener("click", () => this.handleSubmit());
        container.append(this.selectEl, this.inputsContainer, this.submitButton);
        this.root.replaceChildren(title, container);
        this.unsubscribe = this.store.subscribe((state) => this.render(state));
    }
    destroy() {
        this.unsubscribe?.();
        this.selectEl?.removeEventListener("change", () => this.handleSelectChange());
        this.submitButton?.removeEventListener("click", () => this.handleSubmit());
    }
    handleSelectChange() {
        if (!this.selectEl) {
            return;
        }
        this.selectedActionId = this.selectEl.value || null;
        this.renderInputs();
    }
    handleSubmit() {
        if (!this.selectedActionId || !this.onSubmit || !this.inputsContainer || !this.submitButton) {
            return;
        }
        const params = {};
        const inputs = Array.from(this.inputsContainer.querySelectorAll("input"));
        for (const input of inputs) {
            if (!input.name) {
                continue;
            }
            params[input.name] = input.value;
        }
        this.submitButton.disabled = true;
        this.onSubmit(this.selectedActionId, params);
        setTimeout(() => {
            if (this.submitButton) {
                this.submitButton.disabled = false;
            }
        }, 300);
    }
    render(state) {
        if (this.submitButton) {
            this.submitButton.disabled = state.status === "running";
        }
        if (this.selectEl) {
            this.populateSelect(state.playerActions);
        }
        this.renderInputs();
    }
    populateSelect(actions) {
        if (!this.selectEl) {
            return;
        }
        const previous = this.selectedActionId;
        this.selectEl.innerHTML = "";
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = actions.length ? "Choose an action..." : "No actions available";
        this.selectEl.appendChild(placeholder);
        for (const action of actions) {
            const option = document.createElement("option");
            option.value = action.id;
            option.textContent = action.label;
            if (action.id === previous) {
                option.selected = true;
            }
            this.selectEl.appendChild(option);
        }
        if (previous && !actions.find((action) => action.id === previous)) {
            this.selectedActionId = null;
        }
        else if (previous) {
            this.selectedActionId = previous;
        }
    }
    renderInputs() {
        if (!this.inputsContainer) {
            return;
        }
        const actions = this.store.getState().playerActions;
        const action = actions.find((entry) => entry.id === this.selectedActionId);
        this.inputsContainer.innerHTML = "";
        if (!action) {
            return;
        }
        for (const requirement of action.requires) {
            const field = document.createElement("label");
            field.className = "fd-action-panel__field";
            const span = document.createElement("span");
            span.textContent = requirement;
            const input = document.createElement("input");
            input.name = requirement;
            input.type = requirement === "x" || requirement === "y" ? "number" : "text";
            input.placeholder = requirement;
            field.append(span, input);
            this.inputsContainer.appendChild(field);
        }
    }
}
