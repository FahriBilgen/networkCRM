import { NODE_TYPES } from '../types';
import type { EdgeResponse, NodeResponse, NodeType } from '../types';

type Position = { x: number; y: number };
type PositionMap = Record<string, Position>;

const radiusByType: Record<NodeType, number> = {
  [NODE_TYPES.VISION]: 120,
  [NODE_TYPES.GOAL]: 320,
  [NODE_TYPES.PROJECT]: 520,
  [NODE_TYPES.PERSON]: 720,
};

const defaultOrder: NodeType[] = [NODE_TYPES.VISION, NODE_TYPES.GOAL, NODE_TYPES.PROJECT, NODE_TYPES.PERSON];

/**
 * Generates a simple layered mind-map layout. Nodes are grouped by type and placed on
 * concentric circles so that visions stay near the center, hedef/project katmanları orta halkada,
 * kişiler ise dış halkada görünür. Şu an için edge bilgisi sadece ilerideki geliştirmeler için kabul ediliyor.
 */
export function computeMindMapLayout(nodes: NodeResponse[], links: EdgeResponse[] = []): PositionMap {
  if (!nodes?.length) {
    return {};
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _linkCount = links.length; // yer tutucu; ilerideki ebeveyn-çocuk hizalamaları için kullanılacak

  const grouped: Record<NodeType, NodeResponse[]> = {
    [NODE_TYPES.VISION]: [],
    [NODE_TYPES.GOAL]: [],
    [NODE_TYPES.PROJECT]: [],
    [NODE_TYPES.PERSON]: [],
  };

  nodes.forEach((node) => {
    if (grouped[node.type]) {
      grouped[node.type].push(node);
    }
  });

  const positions: PositionMap = {};

  defaultOrder.forEach((type, layerIndex) => {
    const group = grouped[type];
    if (!group || group.length === 0) {
      return;
    }

    const sorted = [...group].sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));
    const isSingleVisionLayer = type === NODE_TYPES.VISION && sorted.length === 1;
    const radius = isSingleVisionLayer ? 0 : radiusByType[type];
    const angleStep = group.length === 1 ? 0 : (Math.PI * 2) / group.length;

    sorted.forEach((node, index) => {
      const angle = angleStep * index + layerIndex * 0.2;
      const baseX = radius * Math.cos(angle);
      const baseY = radius * Math.sin(angle);
      positions[node.id] = {
        x: isSingleVisionLayer ? 0 : baseX,
        y: isSingleVisionLayer ? 0 : baseY,
      };
    });
  });

  const placedNodes = Object.entries(positions);
  if (placedNodes.length === 0) {
    return {};
  }

  const minX = Math.min(...placedNodes.map(([, pos]) => pos.x));
  const minY = Math.min(...placedNodes.map(([, pos]) => pos.y));
  const offsetX = minX < 0 ? -minX + 80 : 0;
  const offsetY = minY < 0 ? -minY + 80 : 0;

  const adjusted: PositionMap = {};
  placedNodes.forEach(([id, pos]) => {
    adjusted[id] = {
      x: Math.round(pos.x + offsetX),
      y: Math.round(pos.y + offsetY),
    };
  });

  return adjusted;
}
