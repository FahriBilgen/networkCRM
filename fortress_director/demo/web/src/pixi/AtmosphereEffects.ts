import { Application, ColorMatrixFilter, Graphics } from "pixi.js";

interface AtmosphereDescriptor {
  mood: string;
  visual: string;
  audio: string;
}

export class AtmosphereEffects {
  private readonly app: Application;
  private overlay: Graphics;
  private warmFilter: ColorMatrixFilter;
  private flickerId: number | null = null;
  private windId: number | null = null;

  constructor(app: Application) {
    this.app = app;
    this.overlay = new Graphics();
    this.overlay.visible = false;
    this.overlay.eventMode = "none";
    this.warmFilter = new ColorMatrixFilter();
    this.app.stage.addChild(this.overlay);
  }

  apply(descriptor: AtmosphereDescriptor, audioHint?: string): void {
    const mood = descriptor.mood?.toLowerCase() ?? "";
    const audio = (audioHint ?? descriptor.audio ?? "").toLowerCase();
    const state = resolveAtmosphereState(mood, audio);
    this.updateOverlay(state.overlay ? mood : "");
    this.updateWarmFilter(state.warm);
    this.applyWind(state.wind);
    this.applyFlicker(state.fire);
  }

  private updateOverlay(mood: string): void {
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

  private updateWarmFilter(enabled: boolean): void {
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
    } else {
      stage.filters = null;
    }
  }

  private applyFlicker(enabled: boolean): void {
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

  private applyWind(enabled: boolean): void {
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

export function resolveAtmosphereState(mood: string, audio: string): {
  overlay: boolean;
  warm: boolean;
  wind: boolean;
  fire: boolean;
} {
  const normalizedMood = mood?.toLowerCase() ?? "";
  const normalizedAudio = audio?.toLowerCase() ?? "";
  return {
    overlay: normalizedMood === "grim" || normalizedMood === "collapse",
    warm: normalizedMood === "hopeful",
    wind: normalizedAudio === "wind",
    fire: normalizedAudio === "fire"
  };
}
