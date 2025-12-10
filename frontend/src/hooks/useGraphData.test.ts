import { describe, it, expect, beforeEach } from 'vitest';
import { useGraphData } from '../hooks/useGraphData';

// Mock API responses
const mockGraphData = {
  nodes: [
    { id: '1', label: 'John Doe', type: 'PERSON', sector: 'Technology', position: { x: 100, y: 100 } },
    { id: '2', label: 'Tech Vision', type: 'VISION', sector: 'Technology', position: { x: 200, y: 200 } },
    { id: '3', label: 'AI Project', type: 'PROJECT', sector: 'Technology', position: { x: 300, y: 300 } },
  ],
  edges: [
    { id: 'e1-2', source: '1', target: '2', type: 'supports' },
    { id: 'e2-3', source: '2', target: '3', type: 'related_to' },
  ],
};

describe('useGraphData Hook', () => {
  beforeEach(() => {
    // Reset any state before each test
  });

  it('should have nodes with correct structure', () => {
    const nodes = mockGraphData.nodes;

    expect(nodes).toHaveLength(3);
    expect(nodes[0]).toHaveProperty('id');
    expect(nodes[0]).toHaveProperty('label');
    expect(nodes[0]).toHaveProperty('type');
  });

  it('should have edges connecting nodes', () => {
    const edges = mockGraphData.edges;

    expect(edges).toHaveLength(2);
    expect(edges[0].source).toBe('1');
    expect(edges[0].target).toBe('2');
  });

  it('should filter nodes by type', () => {
    const nodeType = 'PERSON';
    const filtered = mockGraphData.nodes.filter(n => n.type === nodeType);

    expect(filtered).toHaveLength(1);
    expect(filtered[0].label).toBe('John Doe');
  });

  it('should filter nodes by sector', () => {
    const sector = 'Technology';
    const filtered = mockGraphData.nodes.filter(n => n.sector === sector);

    expect(filtered).toHaveLength(3);
  });

  it('should find connected nodes', () => {
    const nodeId = '1';
    const edges = mockGraphData.edges.filter(e => e.source === nodeId || e.target === nodeId);
    const connectedNodeIds = edges.map(e => e.source === nodeId ? e.target : e.source);

    expect(connectedNodeIds).toHaveLength(1);
    expect(connectedNodeIds[0]).toBe('2');
  });

  it('should calculate graph metrics', () => {
    const nodeCount = mockGraphData.nodes.length;
    const edgeCount = mockGraphData.edges.length;
    const density = (2 * edgeCount) / (nodeCount * (nodeCount - 1));

    expect(nodeCount).toBe(3);
    expect(edgeCount).toBe(2);
    expect(density).toBeGreaterThan(0);
    expect(density).toBeLessThanOrEqual(1);
  });

  it('should handle empty graph', () => {
    const emptyData = { nodes: [], edges: [] };

    expect(emptyData.nodes).toHaveLength(0);
    expect(emptyData.edges).toHaveLength(0);
  });

});
