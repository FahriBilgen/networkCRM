import type { EdgeResponse, NodeResponse, NodeType } from '../types';

export type ClusterBreakdown = {
  id: string;
  nodeIds: string[];
  size: number;
  typeCounts: Partial<Record<NodeType, number>>;
};

export type ClusterStats = {
  clusters: ClusterBreakdown[];
  isolatedNodeIds: string[];
  largestClusterSize: number;
};

export function computeClusterStats(nodes: NodeResponse[], links: EdgeResponse[]): ClusterStats {
  if (!nodes?.length) {
    return { clusters: [], isolatedNodeIds: [], largestClusterSize: 0 };
  }

  const adjacency = new Map<string, Set<string>>();
  nodes.forEach((node) => {
    adjacency.set(node.id, new Set<string>());
  });

  links.forEach((edge) => {
    const sourceSet = adjacency.get(edge.sourceNodeId);
    const targetSet = adjacency.get(edge.targetNodeId);
    if (sourceSet && targetSet) {
      sourceSet.add(edge.targetNodeId);
      targetSet.add(edge.sourceNodeId);
    }
  });

  const visited = new Set<string>();
  const clusters: ClusterBreakdown[] = [];
  const isolated: string[] = [];

  nodes.forEach((node) => {
    if (visited.has(node.id)) {
      return;
    }
    const queue: string[] = [node.id];
    const component: string[] = [];
    visited.add(node.id);

    while (queue.length > 0) {
      const current = queue.shift()!;
      component.push(current);
      const neighbors = adjacency.get(current);
      if (!neighbors) {
        continue;
      }
      neighbors.forEach((neighbor) => {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          queue.push(neighbor);
        }
      });
    }

    const breakdown: ClusterBreakdown = {
      id: `cluster-${clusters.length + 1}`,
      nodeIds: component,
      size: component.length,
      typeCounts: {},
    };

    component.forEach((nodeId) => {
      const found = nodes.find((candidate) => candidate.id === nodeId);
      if (found) {
        breakdown.typeCounts[found.type] = (breakdown.typeCounts[found.type] ?? 0) + 1;
      }
    });

    if (breakdown.size === 1 && (adjacency.get(node.id)?.size ?? 0) === 0) {
      isolated.push(node.id);
    }

    clusters.push(breakdown);
  });

  clusters.sort((a, b) => b.size - a.size);

  return {
    clusters,
    isolatedNodeIds: isolated,
    largestClusterSize: clusters[0]?.size ?? 0,
  };
}
