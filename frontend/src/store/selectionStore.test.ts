import { describe, it, expect, beforeEach } from 'vitest';

// Mock selection store
const createSelectionStore = () => {
  let selectedNode: string | null = null;
  let selectedEdges: Set<string> = new Set();

  return {
    setSelectedNode: (id: string | null) => { selectedNode = id; },
    getSelectedNode: () => selectedNode,
    addSelectedEdge: (id: string) => { selectedEdges.add(id); },
    removeSelectedEdge: (id: string) => { selectedEdges.delete(id); },
    getSelectedEdges: () => selectedEdges,
    clearSelection: () => { selectedNode = null; selectedEdges.clear(); },
  };
};

describe('Selection Store', () => {
  let store: any;

  beforeEach(() => {
    store = createSelectionStore();
  });

  it('should select a node', () => {
    store.setSelectedNode('node-1');
    expect(store.getSelectedNode()).toBe('node-1');
  });

  it('should deselect a node', () => {
    store.setSelectedNode('node-1');
    store.setSelectedNode(null);
    expect(store.getSelectedNode()).toBeNull();
  });

  it('should add selected edges', () => {
    store.addSelectedEdge('edge-1');
    store.addSelectedEdge('edge-2');
    expect(store.getSelectedEdges().size).toBe(2);
  });

  it('should remove selected edges', () => {
    store.addSelectedEdge('edge-1');
    store.addSelectedEdge('edge-2');
    store.removeSelectedEdge('edge-1');
    expect(store.getSelectedEdges().size).toBe(1);
  });

  it('should clear all selections', () => {
    store.setSelectedNode('node-1');
    store.addSelectedEdge('edge-1');
    store.clearSelection();

    expect(store.getSelectedNode()).toBeNull();
    expect(store.getSelectedEdges().size).toBe(0);
  });

  it('should not add duplicate edges', () => {
    store.addSelectedEdge('edge-1');
    store.addSelectedEdge('edge-1');
    expect(store.getSelectedEdges().size).toBe(1);
  });

});
