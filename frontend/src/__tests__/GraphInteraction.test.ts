import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSelectionStore } from '../store/selectionStore';
import { useGraphStore } from '../store/graphStore';
import { NODE_TYPES, type NodeResponse } from '../types';

describe('Graph Interaction & Store Integration', () => {
  const mockNode: NodeResponse = {
    id: 'node-1',
    type: NODE_TYPES.PERSON,
    name: 'Test Person',
    description: 'A test node',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  beforeEach(() => {
    useSelectionStore.setState({ selectedNode: null });
    useGraphStore.setState({ 
      graph: { nodes: [], links: [] },
      filteredNodeIds: null 
    });
  });

  it('should select a node and update the store', () => {
    const { result } = renderHook(() => useSelectionStore());

    expect(result.current.selectedNode).toBeNull();

    act(() => {
      result.current.selectNode(mockNode);
    });

    expect(result.current.selectedNode).toEqual(mockNode);
  });

  it('should clear selection', () => {
    const { result } = renderHook(() => useSelectionStore());

    act(() => {
      result.current.selectNode(mockNode);
    });
    expect(result.current.selectedNode).not.toBeNull();

    act(() => {
      result.current.selectNode(null);
    });

    expect(result.current.selectedNode).toBeNull();
  });

  it('should filter nodes in graph store', () => {
    const { result } = renderHook(() => useGraphStore());

    expect(result.current.filteredNodeIds).toBeNull();

    const filterIds = ['node-1', 'node-2'];
    act(() => {
      result.current.setFilteredNodeIds(filterIds);
    });

    expect(result.current.filteredNodeIds).toEqual(filterIds);

    act(() => {
      result.current.clearFilteredNodeIds();
    });

    expect(result.current.filteredNodeIds).toBeNull();
  });

  it('should manage favorite paths', () => {
    const { result } = renderHook(() => useGraphStore());
    const mockPath = {
      id: 'path-1',
      label: 'My Path',
      nodeIds: ['n1', 'n2'],
      goalId: 'g1',
      userId: 'u1',
      createdAt: '2025-01-01'
    };

    act(() => {
      result.current.addFavoritePath(mockPath);
    });

    expect(result.current.favoritePaths).toHaveLength(1);
    expect(result.current.favoritePaths[0]).toEqual(mockPath);

    act(() => {
      result.current.removeFavoritePath('path-1');
    });

    expect(result.current.favoritePaths).toHaveLength(0);
  });
});
