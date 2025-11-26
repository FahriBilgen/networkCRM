import { Application, Container, Graphics, Point, Sprite, Texture } from "pixi.js";

import type { UIGameState } from "../types/ui";
import { AtmosphereEffects } from "./AtmosphereEffects.js";

interface MapRendererOptions {
  gridSize?: number;
  padding?: number;
  tileSize?: number;
}

interface AnimationState {
  from: Point;
  to: Point;
  start: number;
  duration: number;
}

interface MarkerAnimation {
  sprite: Container;
  start: number;
  duration: number;
}

export interface MapRendererSnapshot {
  tileCount: number;
  npcCount: number;
  structureCount: number;
  markerCount: number;
}

const DEFAULT_GRID_SIZE = 12;
const NPC_MOVE_DURATION = 420;
const MARKER_POP_DURATION = 320;

export class MapRenderer {
  private readonly host: HTMLElement;
  private readonly options: MapRendererOptions;
  private app?: Application;
  private tileLayer?: Container;
  private structureLayer?: Container;
  private npcLayer?: Container;
  private markerLayer?: Container;
  private effectsLayer?: Container;
  private tileSize = 48;
  private padding = 24;
  private tileTextures: Texture[] | null = null;
  private npcSprites = new Map<
    string,
    {
      sprite: Graphics;
      animation?: AnimationState;
      data: UIGameState["npcPositions"][string];
    }
  >();
  private structureSprites = new Map<string, Container>();
  private markerMetas = new Map<string, MarkerAnimation>();
  private previousState: UIGameState | null = null;
  private selectionHighlight?: Graphics;
  private tooltipEl: HTMLDivElement | null = null;
  private hoverId: string | null = null;
  private atmosphereFx: AtmosphereEffects | null = null;
  private fireTextures: Texture[] | null = null;

  constructor(host: HTMLElement, options: MapRendererOptions = {}) {
    this.host = host;
    this.options = options;
  }

  /**
   * Provide external tile textures (tileset) so renderer can use sprites instead
   * of vector-drawn tiles. Caller can load assets via PIXI.Loader and pass
   * an array of `Texture` objects matching the grid.
   */
  public setTileTextures(textures: Texture[]): void {
    this.tileTextures = textures && textures.length ? textures : null;
    // redraw tilemap to pick up textures if we've already initialized
    if (this.app) {
      this.drawTilemap(this.options.gridSize ?? DEFAULT_GRID_SIZE);
    }
  }

  /**
   * Provide optional fire animation textures (sprite frames). If set,
   * existing structure flame graphics will be replaced with an animated sprite.
   */
  public setFireTextures(textures: Texture[]): void {
    this.fireTextures = textures && textures.length ? textures : null;
    if (!this.structureLayer) {
      return;
    }
    // Replace existing flame graphics with sprites where applicable
    for (const [, container] of this.structureSprites.entries()) {
      const hasFlame = container.getChildAt(1);
      if (this.fireTextures) {
        // create a sprite from first frame and replace
        const sprite = new Sprite(this.fireTextures[0]);
        sprite.width = this.tileSize * 0.5;
        sprite.height = this.tileSize * 0.5;
        sprite.anchor.set(0.5, 0.5);
        sprite.visible = hasFlame ? (hasFlame.visible ?? true) : true;
        container.removeChildAt(1);
        container.addChild(sprite);
      } else {
        // ensure a fallback Graphics exists
        const flame = new Graphics();
        flame.beginFill(0xff7b00, 0.8);
        flame.drawCircle(0, -this.tileSize * 0.2, this.tileSize * 0.25);
        flame.endFill();
        flame.blendMode = "add";
        flame.visible = false;
        container.removeChildAt(1);
        container.addChild(flame);
      }
    }
  }

  async init(): Promise<void> {
    const gridSize = this.options.gridSize ?? DEFAULT_GRID_SIZE;
    this.padding = this.options.padding ?? 24;
    this.tileSize = this.options.tileSize ?? this.computeTileSize(gridSize);

    this.app = new Application();
    await this.app.init({
      width: gridSize * this.tileSize + this.padding * 2,
      height: gridSize * this.tileSize + this.padding * 2,
      backgroundAlpha: 0,
      antialias: true,
      autoDensity: true,
      resolution: window.devicePixelRatio || 1
    });

    this.tileLayer = new Container();
    this.structureLayer = new Container();
    this.npcLayer = new Container();
    this.markerLayer = new Container();
    this.effectsLayer = new Container();

    this.app.stage.addChild(this.tileLayer, this.structureLayer, this.npcLayer, this.markerLayer, this.effectsLayer);

    this.host.replaceChildren(this.app.canvas);
    this.drawTilemap(gridSize);
    this.selectionHighlight = this.createSelectionHighlight();
    this.app.stage.addChild(this.selectionHighlight);
    this.registerInteraction();
    this.atmosphereFx = new AtmosphereEffects(this.app);
  }

  destroy(): void {
    this.app?.destroy(true, true);
    this.tooltipEl?.remove();
    this.tooltipEl = null;
    this.host.replaceChildren();
    this.npcSprites.clear();
    this.structureSprites.clear();
    this.markerMetas.clear();
    this.previousState = null;
    this.atmosphereFx = null;
  }

  update(state: UIGameState): void {
    if (!this.app) {
      return;
    }
    this.previousState = state;
    this.syncStructures(state);
    this.syncNpcs(state);
    this.syncMarkers(state);
  }

  /**
   * Public API: animate an NPC moving from one grid position to another.
   * Duration will be clamped into the preferred window (350-500ms).
   */
  public animateMove(npcId: string, from: { x: number; y: number }, to: { x: number; y: number }, duration?: number): void {
    const entry = this.npcSprites.get(npcId);
    if (!entry) {
      return;
    }
    const now = performance.now();
    const dur = Math.max(350, Math.min(500, duration ?? NPC_MOVE_DURATION));
    entry.animation = {
      from: new Point(this.padding + from.x * this.tileSize + this.tileSize / 2, this.padding + from.y * this.tileSize + this.tileSize / 2),
      to: new Point(this.padding + to.x * this.tileSize + this.tileSize / 2, this.padding + to.y * this.tileSize + this.tileSize / 2),
      start: now,
      duration: dur
    };
    this.animateNpc(entry as any);
  }

  applyAtmosphere(state: UIGameState["atmosphere"], audioHint?: string): void {
    this.atmosphereFx?.apply(state, audioHint);
  }

  triggerPulse(): void {
    if (!this.app) {
      return;
    }
    this.app.stage.alpha = 0.85;
    window.setTimeout(() => {
      if (this.app) {
        this.app.stage.alpha = 1;
      }
    }, 250);
  }

  shake(duration = 300, intensity = 5): void {
    if (!this.app) {
      return;
    }
    const stage = this.app.stage;
    const original = new Point(stage.x, stage.y);
    const start = performance.now();
    const tick = () => {
      const elapsed = performance.now() - start;
      if (elapsed >= duration) {
        stage.position.copyFrom(original);
        return;
      }
      const progress = 1 - elapsed / duration;
      stage.x = original.x + (Math.random() - 0.5) * intensity * progress;
      stage.y = original.y + (Math.random() - 0.5) * intensity * progress;
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  getSnapshot(): MapRendererSnapshot {
    return {
      tileCount: this.tileLayer?.children.length ?? 0,
      npcCount: this.npcSprites.size,
      structureCount: this.structureLayer?.children.length ?? 0,
      markerCount: this.markerLayer?.children.length ?? 0
    };
  }

  private drawTilemap(gridSize: number): void {
    if (!this.tileLayer) {
      return;
    }
    this.tileLayer.removeChildren();
    for (let y = 0; y < gridSize; y += 1) {
      for (let x = 0; x < gridSize; x += 1) {
        if (this.tileTextures && this.tileTextures.length) {
          // Pick a texture by an index derived from coordinates so the map looks varied
          const idx = (x + y * gridSize) % this.tileTextures.length;
          const sprite = new Sprite(this.tileTextures[idx]);
          sprite.width = this.tileSize;
          sprite.height = this.tileSize;
          sprite.position.set(this.padding + x * this.tileSize, this.padding + y * this.tileSize);
          this.tileLayer.addChild(sprite);
        } else {
          const tile = new Graphics();
          tile.rect(0, 0, this.tileSize, this.tileSize);
          const isDark = (x + y) % 2 === 0;
          tile.beginFill(isDark ? 0x0f172a : 0x111827, 1);
          tile.drawRect(0, 0, this.tileSize, this.tileSize);
          tile.endFill();
          tile.lineStyle(1, 0x1f2937, 0.3);
          tile.drawRect(0, 0, this.tileSize, this.tileSize);
          tile.position.set(this.padding + x * this.tileSize, this.padding + y * this.tileSize);
          this.tileLayer.addChild(tile);
        }
      }
    }
  }

  private computeTileSize(gridSize: number): number {
    const maxWidth = this.host.clientWidth || 560;
    const margin = 48;
    return Math.max(32, Math.floor((maxWidth - margin) / gridSize));
  }

  private syncStructures(state: UIGameState): void {
    if (!this.structureLayer) {
      return;
    }
    const seen = new Set<string>();
    for (const [id, entry] of Object.entries(state.structures)) {
      seen.add(id);
      const sprite = this.structureSprites.get(id) ?? this.createStructureSprite();
      const ratio = entry.maxIntegrity > 0 ? entry.integrity / entry.maxIntegrity : 1;
      sprite.position.set(...this.entityToCanvas(entry));
      sprite.scale.set(1);
      const graphics = sprite.getChildAt(0) as Graphics;
      graphics.clear();
      const color = ratio > 0.66 ? 0x4ade80 : ratio > 0.33 ? 0xfacc15 : 0xf87171;
      graphics.beginFill(color, 0.5 + ratio * 0.5);
      graphics.drawRoundedRect(
        -this.tileSize * 0.45,
        -this.tileSize * 0.45,
        this.tileSize * 0.9,
        this.tileSize * 0.9,
        6
      );
      graphics.endFill();
      if (entry.on_fire) {
        const flame = sprite.getChildAt(1) as Graphics;
        flame.visible = true;
        flame.alpha = 0.6 + Math.random() * 0.3;
        flame.scale.set(0.7 + Math.random() * 0.2);
      } else {
        (sprite.getChildAt(1) as Graphics).visible = false;
      }
      if (!this.structureSprites.has(id)) {
        this.structureLayer.addChild(sprite);
        this.structureSprites.set(id, sprite);
      }
      this.attachTooltip(sprite, `${entry.kind ?? "Structure"}\nIntegrity: ${entry.integrity}%`);
    }
    for (const [id, sprite] of this.structureSprites.entries()) {
      if (!seen.has(id)) {
        sprite.destroy();
        this.structureSprites.delete(id);
      }
    }
  }

  private createStructureSprite(): Container {
    const container = new Container();
    container.eventMode = "static";
    container.cursor = "pointer";
    const block = new Graphics();
    const flame = new Graphics();
    flame.beginFill(0xff7b00, 0.8);
    flame.drawCircle(0, -this.tileSize * 0.2, this.tileSize * 0.25);
    flame.endFill();
    flame.blendMode = "add";
    flame.visible = false;
    container.addChild(block, flame);
    return container;
  }

  private syncNpcs(state: UIGameState): void {
    if (!this.npcLayer) {
      return;
    }
    const seen = new Set<string>();
    const now = performance.now();
    for (const [id, payload] of Object.entries(state.npcPositions)) {
      seen.add(id);
      const existing = this.npcSprites.get(id);
      if (!existing) {
        const sprite = this.createNpcSprite(payload);
        this.npcLayer.addChild(sprite);
        this.npcSprites.set(id, { sprite, data: payload });
        sprite.position.set(...this.entityToCanvas(payload));
        this.attachTooltip(
          sprite,
          `${payload.name ?? id}\nHealth ${payload.health}% | Morale ${payload.morale}%`
        );
        continue;
      }
      const [targetX, targetY] = this.entityToCanvas(payload);
      const [currentX, currentY] = this.entityToCanvas(existing.data);
      const moved = currentX !== targetX || currentY !== targetY;
      existing.data = payload;
      this.applyNpcVisuals(existing.sprite, payload);
      this.attachTooltip(
        existing.sprite,
        `${payload.name ?? id}\nHealth ${payload.health}% | Morale ${payload.morale}%`
      );
      if (moved) {
        existing.animation = {
          from: new Point(currentX, currentY),
          to: new Point(targetX, targetY),
          start: now,
          duration: NPC_MOVE_DURATION
        };
        this.animateNpc(existing);
      } else {
        existing.sprite.position.set(targetX, targetY);
      }
    }
    for (const [id, entry] of this.npcSprites.entries()) {
      if (!seen.has(id)) {
        entry.sprite.destroy();
        this.npcSprites.delete(id);
      }
    }
  }

  private animateNpc(entry: {
    sprite: Graphics;
    animation?: AnimationState;
  }): void {
    if (!entry.animation) {
      return;
    }
    const tick = () => {
      if (!entry.animation) {
        return;
      }
      const elapsed = performance.now() - entry.animation.start;
      const ratio = Math.min(1, elapsed / entry.animation.duration);
      const ease = ratio === 1 ? 1 : 1 - Math.pow(1 - ratio, 3);
      entry.sprite.x = lerp(entry.animation.from.x, entry.animation.to.x, ease);
      entry.sprite.y = lerp(entry.animation.from.y, entry.animation.to.y, ease);
      if (ratio < 1) {
        requestAnimationFrame(tick);
      } else {
        entry.sprite.position.copyFrom(entry.animation.to);
        entry.animation = undefined;
      }
    };
    requestAnimationFrame(tick);
  }

  private createNpcSprite(payload: UIGameState["npcPositions"][string]): Graphics {
    const circle = new Graphics();
    circle.eventMode = "static";
    circle.cursor = "pointer";
    circle.pivot.set(0);
    this.applyNpcVisuals(circle, payload);
    return circle;
  }

  private applyNpcVisuals(sprite: Graphics, payload: UIGameState["npcPositions"][string]): void {
    const radius = this.tileSize * 0.28;
    const color = payload.health < 50 ? 0xff6b6b : payload.hostile ? 0xf87171 : 0x38bdf8;
    sprite.clear();
    sprite.beginFill(color, 0.95);
    sprite.drawCircle(0, 0, radius);
    sprite.endFill();
    sprite.lineStyle(2, 0xffffff, 0.4);
    sprite.drawCircle(0, 0, radius);
    sprite.alpha = payload.fatigue > 65 ? 0.55 : 1;
  }

  private syncMarkers(state: UIGameState): void {
    if (!this.markerLayer) {
      return;
    }
    const seen = new Set<string>();
    const now = performance.now();
    for (const marker of state.eventMarkers) {
      seen.add(marker.id);
      let container = this.markerLayer.children.find((child) => child.name === marker.id) as Container | undefined;
      if (!container) {
        container = this.createMarkerSprite(marker);
        container.name = marker.id;
        this.markerLayer.addChild(container);
        this.markerMetas.set(marker.id, {
          sprite: container,
          start: now,
          duration: MARKER_POP_DURATION
        });
        this.animateMarker(marker.id);
      }
      container.position.set(...this.entityToCanvas(marker));
      this.attachTooltip(container, `${marker.description || "Event"}\nSeverity ${marker.severity}`);
    }
    for (const child of [...this.markerLayer.children]) {
      if (!seen.has(child.name ?? "")) {
        if (child.name) {
          this.markerMetas.delete(child.name);
        }
        child.destroy();
      }
    }
  }

  private animateMarker(id: string): void {
    const meta = this.markerMetas.get(id);
    if (!meta) {
      return;
    }
    const tick = () => {
      const elapsed = performance.now() - meta.start;
      const ratio = Math.min(1, elapsed / meta.duration);
      const scale = easeOutBack(ratio);
      meta.sprite.scale.set(scale);
      if (ratio < 1) {
        requestAnimationFrame(tick);
      } else {
        meta.sprite.scale.set(1);
        this.markerMetas.delete(id);
      }
    };
    meta.sprite.scale.set(0.1);
    requestAnimationFrame(tick);
  }

  private createMarkerSprite(marker: UIGameState["eventMarkers"][number]): Container {
    const container = new Container();
    container.eventMode = "static";
    container.cursor = "pointer";
    const icon = new Graphics();
    const size = this.tileSize * 0.25;
    const color = marker.severity >= 3 ? 0xef4444 : marker.severity === 2 ? 0xf59e0b : 0x38bdf8;
    icon.beginFill(color, 0.9);
    icon.moveTo(0, -size);
    icon.lineTo(size, 0);
    icon.lineTo(0, size);
    icon.lineTo(-size, 0);
    icon.closePath();
    icon.endFill();
    icon.lineStyle(2, 0xffffff, 0.4);
    icon.moveTo(0, -size);
    icon.lineTo(size, 0);
    icon.lineTo(0, size);
    icon.lineTo(-size, 0);
    icon.lineTo(0, -size);
    container.addChild(icon);
    container.scale.set(0.1);
    container.pivot.set(0, 0);
    return container;
  }

  private entityToCanvas(entity: { x: number; y: number }): [number, number] {
    return [
      this.padding + entity.x * this.tileSize + this.tileSize / 2,
      this.padding + entity.y * this.tileSize + this.tileSize / 2
    ];
  }

  private createSelectionHighlight(): Graphics {
    const highlight = new Graphics();
    highlight.lineStyle(2, 0xffffff, 0.4);
    highlight.visible = false;
    return highlight;
  }

  private registerInteraction(): void {
    if (!this.app) {
      return;
    }
    const canvas = this.app.canvas;
    canvas.addEventListener("pointermove", (event) => {
      const bounds = canvas.getBoundingClientRect();
      const x = event.clientX - bounds.left;
      const y = event.clientY - bounds.top;
      this.updateSelectionHighlight(x, y);
    });
    canvas.addEventListener("mouseleave", () => {
      if (this.selectionHighlight) {
        this.selectionHighlight.visible = false;
      }
      this.hideTooltip();
    });
  }

  private updateSelectionHighlight(x: number, y: number): void {
    if (!this.selectionHighlight || !this.previousState) {
      return;
    }
    const gridSize = this.options.gridSize ?? DEFAULT_GRID_SIZE;
    const tileX = Math.floor((x - this.padding) / this.tileSize);
    const tileY = Math.floor((y - this.padding) / this.tileSize);
    if (tileX < 0 || tileY < 0 || tileX >= gridSize || tileY >= gridSize) {
      this.selectionHighlight.visible = false;
      return;
    }
    this.selectionHighlight.visible = true;
    this.selectionHighlight.clear();
    this.selectionHighlight.lineStyle(2, 0xffffff, 0.3);
    this.selectionHighlight.drawRect(
      this.padding + tileX * this.tileSize,
      this.padding + tileY * this.tileSize,
      this.tileSize,
      this.tileSize
    );
  }

  private attachTooltip(displayObject: Container, text: string): void {
    if (!this.tooltipEl) {
      this.tooltipEl = document.createElement("div");
      this.tooltipEl.className = "fd-map-tooltip";
      this.tooltipEl.style.position = "absolute";
      this.tooltipEl.style.pointerEvents = "none";
      this.host.appendChild(this.tooltipEl);
    }
    const carrier = displayObject as Container & {
      __fdTooltipText?: string;
      __fdTooltipAttached?: boolean;
    };
    carrier.__fdTooltipText = text;
    if (carrier.__fdTooltipAttached) {
      return;
    }
    carrier.eventMode = "static";
    carrier.cursor = "pointer";
    carrier.on("pointerover", (event) => {
      const content = (event.currentTarget as typeof carrier).__fdTooltipText ?? text;
      this.tooltipEl!.textContent = content;
      this.tooltipEl!.style.display = "block";
      this.hoverId = displayObject.name ?? null;
      this.positionTooltip(event.global.x, event.global.y);
    });
    carrier.on("pointermove", (event) => {
      if (this.tooltipEl?.style.display === "block") {
        this.positionTooltip(event.global.x, event.global.y);
      }
    });
    carrier.on("pointerout", () => {
      this.hideTooltip();
    });
    carrier.__fdTooltipAttached = true;
  }

  private positionTooltip(pageX: number, pageY: number): void {
    if (!this.tooltipEl) {
      return;
    }
    const rect = this.host.getBoundingClientRect();
    this.tooltipEl.style.left = `${pageX - rect.left + 12}px`;
    this.tooltipEl.style.top = `${pageY - rect.top + 12}px`;
  }

  private hideTooltip(): void {
    if (this.tooltipEl) {
      this.tooltipEl.style.display = "none";
    }
    this.hoverId = null;
  }
}

function lerp(start: number, end: number, t: number): number {
  return start + (end - start) * t;
}

function easeOutBack(value: number): number {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(value - 1, 3) + c1 * Math.pow(value - 1, 2);
}

export function summarizeMap(state: UIGameState, gridSize = DEFAULT_GRID_SIZE): MapRendererSnapshot {
  return {
    tileCount: gridSize * gridSize,
    npcCount: Object.keys(state.npcPositions).length,
    structureCount: Object.keys(state.structures).length,
    markerCount: state.eventMarkers.length
  };
}
