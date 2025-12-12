import { describe, expect, it } from 'vitest';
import { computeAutoLayout } from './autoLayout';
import { EDGE_TYPES, NODE_TYPES } from '../types';

describe('computeAutoLayout', () => {
  it('returns coordinates for nodes when graph data exists', async () => {
    const nodes = [
      { id: 'vision-1', type: NODE_TYPES.VISION, name: 'Vision' },
      { id: 'goal-1', type: NODE_TYPES.GOAL, name: 'Goal' },
      { id: 'person-1', type: NODE_TYPES.PERSON, name: 'Person 1' },
    ] as any;
    const edges = [
      { id: 'edge-vision-goal', sourceNodeId: 'goal-1', targetNodeId: 'vision-1', type: EDGE_TYPES.BELONGS_TO },
      { id: 'edge-person-goal', sourceNodeId: 'person-1', targetNodeId: 'goal-1', type: EDGE_TYPES.SUPPORTS },
    ] as any;

    const positions = await computeAutoLayout(nodes, edges);

    expect(Object.keys(positions)).toHaveLength(3);
    expect(positions['vision-1']).toBeDefined();
    expect(positions['goal-1']).toBeDefined();
  });

  it('returns empty object when no nodes exist', async () => {
    const positions = await computeAutoLayout([], []);
    expect(positions).toEqual({});
  });
});
