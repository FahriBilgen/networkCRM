import type { EdgeResponse, GraphResponse, GoalPathSuggestion } from '../types';
import { NODE_TYPES } from '../types';

type ComputeArgs = {
  goalId: string;
  graph: Pick<GraphResponse, 'nodes' | 'links'>;
  maxDepth?: number;
  maxSuggestions?: number;
};

export function computeGoalPathSuggestions({
  goalId,
  graph,
  maxDepth = 3,
  maxSuggestions = 3,
}: ComputeArgs): GoalPathSuggestion[] {
  const nodeMap = new Map(graph.nodes.map((node) => [node.id, node]));
  if (!nodeMap.has(goalId)) {
    return [];
  }
  const adjacency = buildAdjacency(graph.links, nodeMap);
  const visited = new Set<string>([goalId]);
  const queue: Array<{ nodeId: string; path: string[] }> = [{ nodeId: goalId, path: [goalId] }];
  const suggestions: GoalPathSuggestion[] = [];
  const includedPeople = new Set<string>();

  while (queue.length > 0) {
    const { nodeId, path } = queue.shift()!;
    const distance = path.length - 1;
    if (distance > maxDepth) {
      continue;
    }

    if (nodeId !== goalId) {
      const node = nodeMap.get(nodeId);
      if (node?.type === NODE_TYPES.PERSON && distance >= 2 && !includedPeople.has(nodeId)) {
        suggestions.push({
          person: node,
          distance,
          pathNodeIds: [...path],
        });
        includedPeople.add(nodeId);
        if (suggestions.length >= maxSuggestions) {
          break;
        }
      }
    }

    const neighbors = adjacency.get(nodeId);
    if (!neighbors) {
      continue;
    }
    neighbors.forEach((neighborId) => {
      if (!visited.has(neighborId)) {
        visited.add(neighborId);
        queue.push({ nodeId: neighborId, path: [...path, neighborId] });
      }
    });
  }

  return suggestions;
}

function buildAdjacency(links: EdgeResponse[], nodeMap: Map<string, NodeResponse>) {
  const adjacency = new Map<string, Set<string>>();
  nodeMap.forEach((_node, id) => adjacency.set(id, new Set()));
  links.forEach((edge) => {
    if (!nodeMap.has(edge.sourceNodeId) || !nodeMap.has(edge.targetNodeId)) {
      return;
    }
    adjacency.get(edge.sourceNodeId)?.add(edge.targetNodeId);
    adjacency.get(edge.targetNodeId)?.add(edge.sourceNodeId);
  });
  return adjacency;
}
