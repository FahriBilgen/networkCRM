import { ColorMatrixFilter, Graphics } from "pixi.js";
export class AtmosphereEffects {
    constructor(app) {
        Object.defineProperty(this, "app", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "overlay", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "warmFilter", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: void 0
        });
        Object.defineProperty(this, "flickerId", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        Object.defineProperty(this, "windId", {
            enumerable: true,
            configurable: true,
            writable: true,
            value: null
        });
        this.app = app;
        this.overlay = new Graphics();
        this.overlay.visible = false;
        this.overlay.eventMode = "none";
        this.warmFilter = new ColorMatrixFilter();
        this.app.stage.addChild(this.overlay);
    }
    apply(descriptor, audioHint) {
        const mood = descriptor.mood?.toLowerCase() ?? "";
        const audio = (audioHint ?? descriptor.audio ?? "").toLowerCase();
        const state = resolveAtmosphereState(mood, audio);
        this.updateOverlay(state.overlay ? mood : "");
        this.updateWarmFilter(state.warm);
        this.applyWind(state.wind);
        this.applyFlicker(state.fire);
    }
    updateOverlay(mood) {
        const needsOverlay = mood === "grim" || mood === "collapse";
        const renderer = this.app.renderer;
        this.overlay.clear();
        if (!needsOverlay) {
            this.overlay.visible = false;
            return;
        }
        this.overlay.visible = true;
        this.overlay.rect(0, 0, renderer.width, renderer.height);
        this.overlay.fill({ color: 0x0f172a, alpha: 0.4 });
    }
    updateWarmFilter(enabled) {
        const stage = this.app.stage;
        if (enabled) {
            this.warmFilter.matrix = [
                1.1,
                0,
                0,
                0,
                0,
                0,
                1.05,
                0,
                0,
                0,
                0,
                0,
                0.95,
                0,
                0,
                0,
                0,
                0,
                1,
                0
            ];
            stage.filters = [this.warmFilter];
        }
        else {
            stage.filters = null;
        }
    }
    applyFlicker(enabled) {
        if (!enabled) {
            if (this.flickerId !== null) {
                cancelAnimationFrame(this.flickerId);
                this.flickerId = null;
                this.overlay.alpha = 0.4;
            }
            return;
        }
        const tick = () => {
            this.overlay.alpha = 0.35 + Math.random() * 0.1;
            this.flickerId = requestAnimationFrame(tick);
        };
        if (this.flickerId === null) {
            this.flickerId = requestAnimationFrame(tick);
        }
    }
    applyWind(enabled) {
        if (!enabled) {
            if (this.windId !== null) {
                cancelAnimationFrame(this.windId);
                this.windId = null;
                this.overlay.y = 0;
            }
            return;
        }
        const start = performance.now();
        const tick = () => {
            const elapsed = performance.now() - start;
            this.overlay.y = Math.sin(elapsed / 2000) * 6;
            this.windId = requestAnimationFrame(tick);
        };
        if (this.windId === null) {
            this.windId = requestAnimationFrame(tick);
        }
    }
}
export function resolveAtmosphereState(mood, audio) {
    const normalizedMood = mood?.toLowerCase() ?? "";
    const normalizedAudio = audio?.toLowerCase() ?? "";
    return {
        overlay: normalizedMood === "grim" || normalizedMood === "collapse",
        warm: normalizedMood === "hopeful",
        wind: normalizedAudio === "wind",
        fire: normalizedAudio === "fire"
    };
}
