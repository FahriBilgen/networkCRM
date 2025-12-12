import { describe, it, expect } from 'vitest';
import { computeClusterStats } from './graphClusters';
import { NODE_TYPES } from '../types';
import type { NodeResponse, EdgeResponse } from '../types';

const node = (id: string, type: NodeResponse['type']): NodeResponse => ({
  id,
  type,
  name: id,
});

describe('computeClusterStats', () => {
  it('detects multiple clusters and isolated nodes', () => {
    const nodes: NodeResponse[] = [
      node('vision-1', NODE_TYPES.VISION),
      node('goal-1', NODE_TYPES.GOAL),
      node('project-1', NODE_TYPES.PROJECT),
      node('person-1', NODE_TYPES.PERSON),
      node('person-2', NODE_TYPES.PERSON),
      node('loner', NODE_TYPES.PERSON),
    ];

    const links: EdgeResponse[] = [
      {
        id: 'edge-1',
        sourceNodeId: 'vision-1',
        targetNodeId: 'goal-1',
        type: 'BELONGS_TO',
      },
      {
        id: 'edge-2',
        sourceNodeId: 'goal-1',
        targetNodeId: 'project-1',
        type: 'BELONGS_TO',
      },
      {
        id: 'edge-3',
        sourceNodeId: 'person-1',
        targetNodeId: 'person-2',
        type: 'KNOWS',
      },
    ];

    const stats = computeClusterStats(nodes, links);

    expect(stats.clusters).toHaveLength(3);
    expect(stats.isolatedNodeIds).toContain('loner');
    expect(stats.largestClusterSize).toBe(3);

    const goalCluster = stats.clusters.find((cluster) => cluster.nodeIds.includes('goal-1'));
    expect(goalCluster?.typeCounts[NODE_TYPES.VISION]).toBe(1);
    expect(goalCluster?.typeCounts[NODE_TYPES.GOAL]).toBe(1);
  });
});
