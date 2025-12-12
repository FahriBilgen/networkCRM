import ELK from 'elkjs/lib/elk.bundled.js';
import type { EdgeResponse, NodeResponse } from '../types';

const elk = new ELK();

export type LayoutPositionMap = Record<string, { x: number; y: number }>;

export async function computeAutoLayout(nodes: NodeResponse[], edges: EdgeResponse[]) {
  if (!nodes.length) {
    return {};
  }
  const elkGraph = buildElkGraph(nodes, edges);
  const layout = await elk.layout(elkGraph);
  const positions: LayoutPositionMap = {};
  layout.children?.forEach((child) => {
    if (child?.id == null) {
      return;
    }
    positions[child.id] = {
      x: Math.round(child.x ?? 0),
      y: Math.round(child.y ?? 0),
    };
  });
  return positions;
}

function buildElkGraph(nodes: NodeResponse[], edges: EdgeResponse[]) {
  return {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'DOWN',
      'elk.layered.spacing.nodeNodeBetweenLayers': '80',
      'elk.spacing.nodeNode': '50',
    },
    children: nodes.map((node) => ({
      id: node.id,
      width: widthForNode(node),
      height: heightForNode(node),
    })),
    edges: edges
      .filter((edge) => edge.sourceNodeId && edge.targetNodeId)
      .map((edge) => ({
        id: edge.id,
        sources: [edge.sourceNodeId],
        targets: [edge.targetNodeId],
      })),
  };
}

function widthForNode(node: NodeResponse) {
  if (node.type === 'VISION') {
    return 260;
  }
  if (node.type === 'GOAL') {
    return 220;
  }
  return 180;
}

function heightForNode(node: NodeResponse) {
  if (node.type === 'VISION') {
    return 120;
  }
  if (node.type === 'GOAL') {
    return 100;
  }
  return 80;
}
