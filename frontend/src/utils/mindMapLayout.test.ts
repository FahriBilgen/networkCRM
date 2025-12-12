import { describe, it, expect } from 'vitest';
import { computeMindMapLayout } from './mindMapLayout';
import { NODE_TYPES } from '../types';
import type { NodeResponse } from '../types';

const baseNode = (id: string, type: NodeResponse['type'], name: string): NodeResponse => ({
  id,
  type,
  name,
});

describe('computeMindMapLayout', () => {
  it('returns deterministic layered positions grouped by node type', () => {
    const nodes: NodeResponse[] = [
      baseNode('vision-1', NODE_TYPES.VISION, 'Ana Vizyon'),
      baseNode('goal-1', NODE_TYPES.GOAL, 'MVP'),
      baseNode('goal-2', NODE_TYPES.GOAL, 'Growth'),
      baseNode('project-1', NODE_TYPES.PROJECT, 'Onboarding'),
      baseNode('person-1', NODE_TYPES.PERSON, 'Ahmet'),
      baseNode('person-2', NODE_TYPES.PERSON, 'Deniz'),
    ];

    const layout = computeMindMapLayout(nodes, []);

    expect(Object.keys(layout)).toHaveLength(nodes.length);
    expect(layout['vision-1']).toBeDefined();
    expect(layout['goal-1']).toBeDefined();
    expect(layout['person-2']).toBeDefined();

    const allPositive = Object.values(layout).every((pos) => pos.x >= 0 && pos.y >= 0);
    expect(allPositive).toBe(true);

    // Farklı katmanlar farklı yarıçaplara sahip olmalı
    const goalDistance = Math.hypot(layout['goal-1'].x - layout['vision-1'].x, layout['goal-1'].y - layout['vision-1'].y);
    const personDistance = Math.hypot(
      layout['person-1'].x - layout['vision-1'].x,
      layout['person-1'].y - layout['vision-1'].y,
    );
    expect(personDistance).toBeGreaterThan(goalDistance);
  });
});
