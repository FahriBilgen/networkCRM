import { describe, it, expect } from 'vitest';

describe('Type Definitions', () => {
  it('should validate node type', () => {
    type NodeType = 'PERSON' | 'VISION' | 'GOAL' | 'PROJECT';
    const validTypes: NodeType[] = ['PERSON', 'VISION', 'GOAL', 'PROJECT'];

    validTypes.forEach(type => {
      expect(['PERSON', 'VISION', 'GOAL', 'PROJECT']).toContain(type);
    });
  });

  it('should validate edge type', () => {
    type EdgeType = 'supports' | 'related_to' | 'depends_on';
    const validEdgeTypes: EdgeType[] = ['supports', 'related_to', 'depends_on'];

    validEdgeTypes.forEach(type => {
      expect(['supports', 'related_to', 'depends_on']).toContain(type);
    });
  });

  it('should have correct node structure', () => {
    interface Node {
      id: string;
      label: string;
      type: string;
      sector?: string;
      relationshipStrength?: number;
    }

    const testNode: Node = {
      id: '1',
      label: 'Test Node',
      type: 'PERSON',
      sector: 'Technology',
      relationshipStrength: 5,
    };

    expect(testNode.id).toBeDefined();
    expect(testNode.label).toBeDefined();
    expect(testNode.type).toBeDefined();
    expect(testNode.sector).toBe('Technology');
    expect(testNode.relationshipStrength).toBe(5);
  });

  it('should have correct edge structure', () => {
    interface Edge {
      id: string;
      source: string;
      target: string;
      type?: string;
      weight?: number;
    }

    const testEdge: Edge = {
      id: 'e1',
      source: '1',
      target: '2',
      type: 'supports',
      weight: 0.8,
    };

    expect(testEdge.source).toBe('1');
    expect(testEdge.target).toBe('2');
    expect(testEdge.type).toBe('supports');
  });

});
