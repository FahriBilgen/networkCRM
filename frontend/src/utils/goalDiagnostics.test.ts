import { describe, expect, it, vi } from 'vitest';
import { buildGoalNetworkDiagnostics } from './goalDiagnostics';
import { EDGE_TYPES, NODE_TYPES } from '../types';

describe('buildGoalNetworkDiagnostics', () => {
  it('summarizes readiness, sectors and risks', () => {
    vi.setSystemTime(new Date('2025-02-01T00:00:00Z'));
    const nodes = [
      { id: 'p1', type: NODE_TYPES.PERSON, name: 'Ahmet', sector: 'Fintech' },
      { id: 'p2', type: NODE_TYPES.PERSON, name: 'Deniz', sector: 'Marketing' },
      { id: 'p3', type: NODE_TYPES.PERSON, name: 'Ece', sector: 'AI' },
    ] as any;
    const supports = [
      {
        id: 's1',
        sourceNodeId: 'p1',
        targetNodeId: 'goal',
        type: EDGE_TYPES.SUPPORTS,
        relationshipStrength: 5,
        lastInteractionDate: '2025-01-20',
      },
      {
        id: 's2',
        sourceNodeId: 'p2',
        targetNodeId: 'goal',
        type: EDGE_TYPES.SUPPORTS,
        relationshipStrength: 2,
        lastInteractionDate: '2024-09-01',
      },
    ];

    const diagnostics = buildGoalNetworkDiagnostics(nodes, supports);

    expect(diagnostics.readiness.level).toBe('medium');
    expect(diagnostics.readiness.summary).toContain('2 baglanti');
    expect(diagnostics.sectorHighlights[0]).toContain('fintech');
    expect(diagnostics.riskAlerts.some((line) => line.includes('gundur iletisim yok'))).toBeTruthy();
    vi.useRealTimers();
  });

  it('handles empty supports gracefully', () => {
    const nodes = [{ id: 'p1', type: NODE_TYPES.PERSON, name: 'Ahmet', sector: 'Fintech' }] as any;
    const diagnostics = buildGoalNetworkDiagnostics(nodes, []);
    expect(diagnostics.readiness.message).toContain('Bu hedefe bagli kisi yok');
    expect(diagnostics.riskAlerts[0]).toContain('Destekci yok');
  });
});
