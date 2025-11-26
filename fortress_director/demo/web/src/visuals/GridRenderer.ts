import { Application, Container, Graphics } from "pixi.js";
import type { GridEntity } from "../types/ui";

const ENTITY_COLORS: Record<string, number> = {
  player: 0x8b5cf6,
  npc: 0x38bdf8,
  marker: 0xf97316,
  item: 0x22c55e
};

interface GridRendererOptions {
  gridSize?: number;
  padding?: number;
}

export class GridRenderer {
  private app?: Application;
  private gridLayer?: Graphics;
  private entityLayer?: Container;
  private tileSize = 48;

  constructor(
    private readonly host: HTMLElement,
    private readonly options: GridRendererOptions = {}
  ) {}

  async init(): Promise<void> {
    const gridSize = this.options.gridSize ?? 12;
    this.tileSize = this.computeTileSize(gridSize);
    const padding = this.options.padding ?? 12;
    const width = gridSize * this.tileSize + padding * 2;
    const height = gridSize * this.tileSize + padding * 2;

    this.app = new Application();
    await this.app.init({
      width,
      height,
      background: "#030712",
      antialias: true,
      autoDensity: true,
      resolution: window.devicePixelRatio || 1
    });
    this.host.replaceChildren(this.app.canvas);

    this.gridLayer = new Graphics();
    this.entityLayer = new Container();
    this.app.stage.addChild(this.gridLayer);
    this.app.stage.addChild(this.entityLayer);
    this.drawGrid(gridSize, padding);
  }

  destroy(): void {
    this.app?.destroy(true, true);
    this.host.replaceChildren();
  }

  setEntities(entities: GridEntity[]): void {
    if (!this.entityLayer) {
      return;
    }
    this.entityLayer.removeChildren();
    const padding = this.options.padding ?? 12;
    for (const entity of entities) {
      const shape = new Graphics();
      const color = entity.color ?? ENTITY_COLORS[entity.entityType] ?? 0xffffff;
      if (entity.entityType === "structure") {
        this.drawStructure(shape, entity, color, padding);
      } else if (entity.entityType === "marker") {
        this.drawMarker(shape, entity, color, padding);
      } else {
        this.drawActor(shape, entity, color, padding);
      }
      this.entityLayer.addChild(shape);
    }
  }

  private drawGrid(gridSize: number, padding: number): void {
    if (!this.gridLayer) {
      return;
    }
    this.gridLayer.clear();
    this.gridLayer.lineStyle(1, 0x2a3357, 0.8);
    this.gridLayer.drawRect(
      padding,
      padding,
      gridSize * this.tileSize,
      gridSize * this.tileSize
    );
    for (let i = 1; i < gridSize; i += 1) {
      const position = padding + i * this.tileSize;
      this.gridLayer.moveTo(position, padding);
      this.gridLayer.lineTo(position, padding + gridSize * this.tileSize);
      this.gridLayer.moveTo(padding, position);
      this.gridLayer.lineTo(padding + gridSize * this.tileSize, position);
    }
    this.gridLayer.lineStyle(2, 0x4c585d, 0.3);
    this.gridLayer.drawRect(
      padding - 4,
      padding - 4,
      gridSize * this.tileSize + 8,
      gridSize * this.tileSize + 8
    );
  }

  private computeTileSize(gridSize: number): number {
    const maxWidth = this.host.clientWidth || 540;
    const margin = 40;
    return Math.max(32, Math.floor((maxWidth - margin) / gridSize));
  }

  private drawActor(shape: Graphics, entity: GridEntity, color: number, padding: number): void {
    const { x, y } = this.toCanvasPosition(entity, padding);
    const radius =
      entity.entityType === "player"
        ? Math.max(8, this.tileSize * 0.4)
        : entity.entityType === "npc"
          ? Math.max(6, this.tileSize * 0.3)
          : Math.max(5, this.tileSize * 0.25);
    shape.lineStyle(entity.entityType === "player" ? 3 : 1, 0xffffff, entity.entityType === "player" ? 0.7 : 0.4);
    shape.beginFill(color, 0.95);
    shape.drawCircle(x, y, radius);
    shape.endFill();
  }

  private drawStructure(shape: Graphics, entity: GridEntity, color: number, padding: number): void {
    const { x, y } = this.toCanvasPosition(entity, padding);
    const size = this.tileSize * 0.65;
    const alpha = entity.integrityRatio ? 0.35 + 0.65 * entity.integrityRatio : 0.8;
    shape.lineStyle(2, 0xffffff, 0.25);
    shape.beginFill(color, alpha);
    shape.drawRoundedRect(x - size / 2, y - size / 2, size, size, 6);
    shape.endFill();
  }

  private drawMarker(shape: Graphics, entity: GridEntity, color: number, padding: number): void {
    const { x, y } = this.toCanvasPosition(entity, padding);
    const severity = entity.severity ?? 1;
    const size = Math.max(6, this.tileSize * (0.2 + 0.1 * severity));
    shape.lineStyle(1.5, 0xffffff, 0.4);
    shape.beginFill(color, 0.95);
    shape.moveTo(x, y - size);
    shape.lineTo(x + size, y);
    shape.lineTo(x, y + size);
    shape.lineTo(x - size, y);
    shape.lineTo(x, y - size);
    shape.endFill();
  }

  private toCanvasPosition(entity: GridEntity, padding: number): { x: number; y: number } {
    return {
      x: padding + entity.x * this.tileSize + this.tileSize / 2,
      y: padding + entity.y * this.tileSize + this.tileSize / 2
    };
  }
}
