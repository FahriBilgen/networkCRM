import { describe, it, expect } from 'vitest';
import { computeGoalPathSuggestions } from './goalPathSuggestions';
import { NODE_TYPES } from '../types';
import type { GraphResponse } from '../types';

const graph: GraphResponse = {
  nodes: [
    { id: 'goal-1', type: NODE_TYPES.GOAL, name: 'Goal' },
    { id: 'person-a', type: NODE_TYPES.PERSON, name: 'Ayse' },
    { id: 'person-b', type: NODE_TYPES.PERSON, name: 'Bora' },
    { id: 'person-c', type: NODE_TYPES.PERSON, name: 'Can' },
    { id: 'person-direct', type: NODE_TYPES.PERSON, name: 'Direct' },
  ],
  links: [
    { id: 'edge-1', sourceNodeId: 'goal-1', targetNodeId: 'person-direct', type: 'SUPPORTS' },
    { id: 'edge-2', sourceNodeId: 'goal-1', targetNodeId: 'person-a', type: 'SUPPORTS' },
    { id: 'edge-3', sourceNodeId: 'person-a', targetNodeId: 'person-b', type: 'KNOWS' },
    { id: 'edge-4', sourceNodeId: 'person-b', targetNodeId: 'person-c', type: 'KNOWS' },
  ],
};

describe('computeGoalPathSuggestions', () => {
  it('returns two-hop suggestions excluding direct supporters', () => {
    const suggestions = computeGoalPathSuggestions({
      goalId: 'goal-1',
      graph,
      maxDepth: 3,
      maxSuggestions: 5,
    });

    expect(suggestions.length).toBeGreaterThan(0);
    expect(suggestions.every((item) => item.distance >= 2)).toBe(true);
    expect(suggestions.some((item) => item.person.id === 'person-b')).toBe(true);
    expect(suggestions.some((item) => item.person.id === 'person-c')).toBe(true);
    expect(suggestions.some((item) => item.person.id === 'person-direct')).toBe(false);
  });

  it('respects max depth by not traversing further', () => {
    const limited = computeGoalPathSuggestions({
      goalId: 'goal-1',
      graph,
      maxDepth: 2,
      maxSuggestions: 5,
    });

    expect(limited.some((item) => item.person.id === 'person-c')).toBe(false);
    expect(limited.some((item) => item.person.id === 'person-b')).toBe(true);
  });
});
