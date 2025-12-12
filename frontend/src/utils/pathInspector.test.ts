import { describe, it, expect } from 'vitest';
import { buildPathDisplay } from './pathInspector';
import { NODE_TYPES } from '../types';

describe('buildPathDisplay', () => {
  it('maps node ids to display metadata', () => {
    const nodes = [
      { id: 'a', type: NODE_TYPES.GOAL, name: 'Goal A', sector: null },
      { id: 'b', type: NODE_TYPES.PERSON, name: 'Bora', sector: 'Fintech' },
    ];

    const display = buildPathDisplay(['a', 'b', 'missing'], nodes as any);

    expect(display).toHaveLength(2);
    expect(display[0]).toMatchObject({ id: 'a', name: 'Goal A', type: NODE_TYPES.GOAL });
    expect(display[1]).toMatchObject({ id: 'b', sector: 'Fintech' });
  });
});
