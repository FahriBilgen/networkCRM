import { describe, it, vi, expect, beforeEach } from 'vitest';
import type { Dispatch, SetStateAction } from 'react';
import {
  createNodeDragHandler,
  strengthToStroke,
  interactionOpacity,
  buildEdgeLabel,
  createEdge,
} from './GraphCanvas';
import { NODE_TYPES } from '../types';
import type { NodeResponse } from '../types';
import { updateNode } from '../api/client';

vi.mock('../api/client', () => ({
  updateNode: vi.fn(() => Promise.resolve({})),
  fetchFavoritePaths: vi.fn(() => Promise.resolve([])),
  deleteFavoritePath: vi.fn(() => Promise.resolve()),
}));

describe('createNodeDragHandler', () => {
  const baseNode: NodeResponse = {
    id: 'node-1',
    type: NODE_TYPES.PERSON,
    name: 'Person 1',
  } as NodeResponse;

  type PositionMap = Record<string, { x: number; y: number }>;
  const setPositionsMock = vi.fn();
  const setStatusMessageMock = vi.fn();
  const setPositions = setPositionsMock as unknown as Dispatch<SetStateAction<PositionMap>>;
  const setStatusMessage = setStatusMessageMock as unknown as Dispatch<SetStateAction<string | null>>;
  const triggerGraphRefresh = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    setPositionsMock.mockReset();
    setStatusMessageMock.mockReset();
    triggerGraphRefresh.mockReset();
  });

  it('persists node position when authenticated', async () => {
    const handler = createNodeDragHandler({
      graphNodes: [baseNode],
      isAuthenticated: true,
      setPositions,
      setStatusMessage,
      triggerGraphRefresh,
    });

    await handler({} as any, { id: 'node-1', position: { x: 40, y: 80 } } as any, []);

    expect(setPositions).toHaveBeenCalled();
    expect(updateNode).toHaveBeenCalledWith(
      'node-1',
      expect.objectContaining({
        properties: expect.objectContaining({
          position: { x: 40, y: 80 },
        }),
      }),
    );
    expect(setStatusMessage).toHaveBeenCalledWith('Kayıt pozisyonu kaydedildi.');
    expect(triggerGraphRefresh).toHaveBeenCalled();
  });

  it('skips update when not authenticated', async () => {
    const handler = createNodeDragHandler({
      graphNodes: [baseNode],
      isAuthenticated: false,
      setPositions,
      setStatusMessage,
      triggerGraphRefresh,
    });

    await handler({} as any, { id: 'node-1', position: { x: 10, y: 20 } } as any, []);
    expect(updateNode).not.toHaveBeenCalled();
  });
});

describe('edge helpers', () => {
  it('calculates stroke width from relationship strength', () => {
    expect(strengthToStroke(undefined)).toBe(1.5);
    expect(strengthToStroke(0)).toBe(1);
    expect(strengthToStroke(5)).toBe(4);
  });

  it('calculates opacity based on last interaction date', () => {
    expect(interactionOpacity(undefined)).toBe(1);
    expect(interactionOpacity('invalid-date')).toBe(1);
    expect(interactionOpacity(new Date().toISOString())).toBeCloseTo(1, 5);
  });

  it('builds descriptive labels and edge style', () => {
    const edge = {
      id: 'edge-1',
      sourceNodeId: 'a',
      targetNodeId: 'b',
      type: 'SUPPORTS' as const,
      relationshipStrength: 4,
      lastInteractionDate: '2025-01-01',
    };
    expect(buildEdgeLabel(edge)).toContain('Destekliyor');
    expect(buildEdgeLabel(edge)).toContain('(4)');
    expect(buildEdgeLabel(edge)).toContain('2025-01-01');

    const created = createEdge(edge);
    expect(created.style?.strokeWidth).toBeCloseTo(strengthToStroke(4));

    const highlighted = createEdge(edge, false, true);
    expect(highlighted.style?.stroke).toBe('#f472b6');
    expect(highlighted.style?.opacity).toBe(1);
  });

  it('dims edges that fall outside the filter', () => {
    const edge = {
      id: 'edge-2',
      sourceNodeId: 'x',
      targetNodeId: 'y',
      type: 'KNOWS' as const,
      relationshipStrength: 2,
    };
    const normal = createEdge(edge);
    const dimmed = createEdge(edge, true);
    const dimmedOpacity = Number(dimmed.style?.opacity ?? 1);
    const normalOpacity = Number(normal.style?.opacity ?? 1);
    expect(dimmedOpacity).toBeLessThan(normalOpacity || 1);
    expect(dimmedOpacity).toBeCloseTo(0.15);
  });
});
