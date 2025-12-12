import type { NodeResponse, NodeType } from '../types';

export type PathDisplayEntry = {
  id: string;
  name: string;
  type: NodeType;
  sector?: string | null;
};

export function buildPathDisplay(pathIds: string[] | null | undefined, nodes: NodeResponse[]): PathDisplayEntry[] {
  if (!pathIds || pathIds.length === 0 || !nodes?.length) {
    return [];
  }
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  return pathIds
    .map((id) => {
      const node = nodeMap.get(id);
      if (!node) {
        return null;
      }
      return {
        id,
        name: node.name ?? 'Isimsiz Node',
        type: node.type,
        sector: node.sector,
      };
    })
    .filter((entry): entry is PathDisplayEntry => Boolean(entry));
}
