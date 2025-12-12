import '@testing-library/jest-dom';
import { describe, it, vi, beforeEach, expect } from 'vitest';
import type { Mock } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { NodeDetailPanel } from './NodeDetailPanel';
import { useSelectionStore } from '../store/selectionStore';
import { useAuthStore } from '../store/authStore';
import { useRefreshStore } from '../store/dataRefreshStore';
import { useGraphStore } from '../store/graphStore';
import {
  filterNodes,
  linkPersonToGoal,
  fetchNodeProximity,
  fetchGoalPathSuggestions,
  updateNode,
} from '../api/client';
import { NODE_TYPES } from '../types';

vi.mock('../api/client', () => ({
  filterNodes: vi.fn(() => Promise.resolve([])),
  linkPersonToGoal: vi.fn(() => Promise.resolve()),
  fetchNodeProximity: vi.fn(() => Promise.resolve(null)),
  fetchGoalPathSuggestions: vi.fn(() => Promise.resolve({ goalId: 'goal-1', suggestions: [] })),
  deleteNode: vi.fn(),
  updateNode: vi.fn(() => Promise.resolve({})),
  createFavoritePath: vi.fn(() =>
    Promise.resolve({
      id: 'fav-1',
      goalId: 'goal-1',
      label: 'Ana Hedef -> Bora',
      nodeIds: ['goal-1', 'person-a', 'person-b'],
    }),
  ),
  deleteFavoritePath: vi.fn(() => Promise.resolve()),
}));

function authenticate() {
  useAuthStore.setState({
    token: 'token',
    email: 'user@test.com',
    loading: false,
    error: null,
    login: async () => {},
    logout: () => {},
  });
}

describe('NodeDetailPanel link person form', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (fetchNodeProximity as unknown as Mock).mockResolvedValue(null);
    authenticate();
    useGraphStore.setState({
      graph: { nodes: [], links: [] } as any,
      filteredNodeIds: null,
      highlightPathNodeIds: null,
      favoritePaths: [],
    });
    useSelectionStore.setState({
      selectedNode: null,
      panelTab: 'details',
      selectNode: (node) => useSelectionStore.setState({ selectedNode: node }),
      setPanelTab: () => {},
    });
    useRefreshStore.setState({
      graphKey: 0,
      visionKey: 0,
      triggerGraphRefresh: () => useRefreshStore.setState((state) => ({ graphKey: state.graphKey + 1 })),
      triggerVisionRefresh: () => useRefreshStore.setState((state) => ({ visionKey: state.visionKey + 1 })),
    });
  });

  it('submits selected person to goal', async () => {
    const goalNode = { id: 'goal-1', type: NODE_TYPES.GOAL, name: 'Goal' } as any;
    const personOptions = [{ id: 'person-1', name: 'Ali', type: NODE_TYPES.PERSON }] as any;
    (filterNodes as unknown as Mock).mockResolvedValueOnce(personOptions);

    render(<NodeDetailPanel />);
    act(() => useSelectionStore.getState().selectNode(goalNode));

    await screen.findByText(/Kisiyi hedefe bagla/i);
    fireEvent.change(screen.getByLabelText(/^Kisi/i), { target: { value: 'person-1' } });
    fireEvent.change(screen.getByLabelText(/Iliski Gucu/i), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText(/^Not$/i), { target: { value: 'critical' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Baglanti Olustur/ }));
    });

    await waitFor(() => {
      expect(linkPersonToGoal).toHaveBeenCalledWith(
        'goal-1',
        expect.objectContaining({ personId: 'person-1', relationshipStrength: 4, notes: 'critical' }),
      );
    });
    expect(screen.getByText(/Baglanti kaydedildi/i)).toBeInTheDocument();
  });

  it('displays proximity metadata when available', async () => {
    (fetchNodeProximity as unknown as Mock).mockResolvedValueOnce({
      nodeId: 'person-1',
      totalConnections: 1,
      connectionCounts: { SUPPORTS: 1 },
      influenceScore: 6,
      neighbors: [
        {
          edgeId: 'edge-1',
          edgeType: 'SUPPORTS',
          outgoing: true,
          neighbor: { id: 'goal-2', type: NODE_TYPES.GOAL, name: 'Goal 2' },
          relationshipStrength: 5,
          lastInteractionDate: '2025-01-10',
        },
      ],
    });

    render(<NodeDetailPanel />);
    act(() =>
      useSelectionStore.getState().selectNode({
        id: 'person-1',
        type: NODE_TYPES.PERSON,
        name: 'Person 1',
      } as any),
    );

    await waitFor(() => {
      expect(screen.getByText(/Iliski gucu: 5/)).toBeInTheDocument();
      expect(screen.getByText(/Son iletisim: 2025-01-10/)).toBeInTheDocument();
      expect(screen.getByText(/Influence skoru/i)).toBeInTheDocument();
    });
  });

  it('highlights nodes by sector when requested', async () => {
    useGraphStore.setState({
      graph: {
        nodes: [
          { id: 'person-1', type: NODE_TYPES.PERSON, name: 'Person 1', sector: 'Fintech' },
          { id: 'person-2', type: NODE_TYPES.PERSON, name: 'Person 2', sector: 'Fintech' },
          { id: 'goal-1', type: NODE_TYPES.GOAL, name: 'Goal 1' },
        ],
        links: [],
      } as any,
      filteredNodeIds: null,
      highlightPathNodeIds: null,
      favoritePaths: [],
    });

    render(<NodeDetailPanel />);
    act(() =>
      useSelectionStore.getState().selectNode({
        id: 'person-1',
        type: NODE_TYPES.PERSON,
        name: 'Person 1',
        sector: 'Fintech',
      } as any),
    );

    await screen.findByText('Fintech');
    fireEvent.click(screen.getByRole('button', { name: /Grafikte vurgula/i }));

    expect(useGraphStore.getState().filteredNodeIds).toEqual(['person-1', 'person-2']);
  });

  it('highlights nodes by tag when tag chip clicked', async () => {
    useGraphStore.setState({
      graph: {
        nodes: [
          { id: 'person-1', type: NODE_TYPES.PERSON, name: 'Person 1', tags: ['mentor'] },
          { id: 'person-2', type: NODE_TYPES.PERSON, name: 'Person 2', tags: ['mentor', 'investor'] },
          { id: 'goal-1', type: NODE_TYPES.GOAL, name: 'Goal 1', tags: ['other'] },
        ],
        links: [],
      } as any,
      filteredNodeIds: null,
      highlightPathNodeIds: null,
      favoritePaths: [],
    });

    render(<NodeDetailPanel />);
    act(() =>
      useSelectionStore.getState().selectNode({
        id: 'person-2',
        type: NODE_TYPES.PERSON,
        name: 'Person 2',
        tags: ['mentor', 'investor'],
      } as any),
    );

    await screen.findByRole('button', { name: 'mentor' });
    fireEvent.click(screen.getByRole('button', { name: 'mentor' }));

    expect(useGraphStore.getState().filteredNodeIds).toEqual(['person-1', 'person-2']);
  });

  it('adds timeline entries for person nodes', async () => {
    useGraphStore.setState({
      graph: {
        nodes: [{ id: 'person-1', type: NODE_TYPES.PERSON, name: 'Person 1' }],
        links: [],
      } as any,
      filteredNodeIds: null,
      highlightPathNodeIds: null,
      favoritePaths: [],
    });

    render(<NodeDetailPanel />);
    act(() =>
      useSelectionStore.getState().selectNode({
        id: 'person-1',
        type: NODE_TYPES.PERSON,
        name: 'Person 1',
      } as any),
    );

    await screen.findByText(/Henuz zaman bazli kayit yok/i);
    const textarea = screen.getByPlaceholderText(/Son gorusme notu/i);
    fireEvent.change(textarea, { target: { value: 'Yeni not' } });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Kaydi ekle/i }));
    });

    await waitFor(() => {
      expect(updateNode).toHaveBeenCalled();
    });
    expect(screen.getByText(/timeline kaydi eklendi/i)).toBeInTheDocument();
    expect(screen.getByText('Yeni not')).toBeInTheDocument();
  });

  it('removes timeline entries when requested', async () => {
    useGraphStore.setState({
      graph: {
        nodes: [
          {
            id: 'person-1',
            type: NODE_TYPES.PERSON,
            name: 'Person 1',
            properties: {
              timeline: [{ id: 'entry-1', date: '2025-01-01', note: 'Eski not' }],
            },
          },
        ],
        links: [],
      } as any,
      filteredNodeIds: null,
      highlightPathNodeIds: null,
      favoritePaths: [],
    });

    render(<NodeDetailPanel />);
    act(() =>
      useSelectionStore.getState().selectNode({
        id: 'person-1',
        type: NODE_TYPES.PERSON,
        name: 'Person 1',
        properties: {
          timeline: [{ id: 'entry-1', date: '2025-01-01', note: 'Eski not' }],
        },
      } as any),
    );

    await screen.findByText('Eski not');
    fireEvent.click(screen.getByRole('button', { name: /Kaydi Sil/i }));

    await waitFor(() => {
      expect(updateNode).toHaveBeenCalledWith(
        'person-1',
        expect.objectContaining({
          properties: expect.objectContaining({
            timeline: [],
          }),
        }),
      );
    });
    expect(screen.getByText(/Timeline kaydi silindi/i)).toBeInTheDocument();
    expect(screen.getByText(/Henuz zaman bazli kayit yok/i)).toBeInTheDocument();
  });

  it('shows path-based suggestions for goals', async () => {
    useGraphStore.setState({
      graph: {
        nodes: [
          { id: 'goal-1', type: NODE_TYPES.GOAL, name: 'Ana Hedef' },
          { id: 'person-a', type: NODE_TYPES.PERSON, name: 'Ayse' },
          { id: 'person-b', type: NODE_TYPES.PERSON, name: 'Bora' },
        ],
        links: [
          { id: 'edge-1', sourceNodeId: 'goal-1', targetNodeId: 'person-a', type: 'SUPPORTS' },
          { id: 'edge-2', sourceNodeId: 'person-a', targetNodeId: 'person-b', type: 'KNOWS' },
        ],
      } as any,
      filteredNodeIds: null,
      highlightPathNodeIds: null,
      favoritePaths: [],
    });

    (fetchGoalPathSuggestions as unknown as Mock).mockResolvedValueOnce({
      goalId: 'goal-1',
      suggestions: [
        {
          person: { id: 'person-b', type: NODE_TYPES.PERSON, name: 'Bora' },
          distance: 2,
          pathNodeIds: ['goal-1', 'person-a', 'person-b'],
        },
      ],
    });

    render(<NodeDetailPanel />);
    act(() =>
      useSelectionStore.getState().selectNode({
        id: 'goal-1',
        type: NODE_TYPES.GOAL,
        name: 'Ana Hedef',
      } as any),
    );

  await screen.findByText(/Path-based oneriler/i);
  expect(screen.getByText('Bora')).toBeInTheDocument();
  await waitFor(() => expect(fetchGoalPathSuggestions).toHaveBeenCalledWith('goal-1', { limit: 4, maxDepth: 3 }));

  fireEvent.click(screen.getAllByRole('button', { name: /Grafikte goster/i })[0]);
    expect(useGraphStore.getState().highlightPathNodeIds).toEqual(
      expect.arrayContaining(['goal-1', 'person-a', 'person-b']),
    );

    fireEvent.click(screen.getAllByRole('button', { name: /Favorilere ekle/i })[0]);
    await waitFor(() => expect(useGraphStore.getState().favoritePaths).toHaveLength(1));
    const favorites = useGraphStore.getState().favoritePaths;
    expect(favorites[0]).toMatchObject({
      goalId: 'goal-1',
    });
    expect(favorites[0].nodeIds).toEqual(expect.arrayContaining(['goal-1', 'person-a', 'person-b']));

  await screen.findByText(/Favori patikalar/i);
  fireEvent.click(screen.getAllByRole('button', { name: /Favoriyi sil/i })[0]);
  await waitFor(() => expect(useGraphStore.getState().favoritePaths).toHaveLength(0));
  });

  it('falls back to local suggestions when API fails', async () => {
    useGraphStore.setState({
      graph: {
        nodes: [
          { id: 'goal-1', type: NODE_TYPES.GOAL, name: 'Ana Hedef' },
          { id: 'person-a', type: NODE_TYPES.PERSON, name: 'Ayse' },
          { id: 'person-b', type: NODE_TYPES.PERSON, name: 'Bora' },
        ],
        links: [
          { id: 'edge-1', sourceNodeId: 'goal-1', targetNodeId: 'person-a', type: 'SUPPORTS' },
          { id: 'edge-2', sourceNodeId: 'person-a', targetNodeId: 'person-b', type: 'KNOWS' },
        ],
      } as any,
      filteredNodeIds: null,
      highlightPathNodeIds: null,
      favoritePaths: [],
    });

    (fetchGoalPathSuggestions as unknown as Mock).mockRejectedValueOnce(new Error('unavailable'));

    render(<NodeDetailPanel />);
    act(() =>
      useSelectionStore.getState().selectNode({
        id: 'goal-1',
        type: NODE_TYPES.GOAL,
        name: 'Ana Hedef',
      } as any),
    );

    await screen.findByText(/Path-based oneriler/i);
    expect(screen.getByText('Bora')).toBeInTheDocument();
    await waitFor(() => expect(fetchGoalPathSuggestions).toHaveBeenCalled());
    expect(screen.getByText(/Yerel graph analizi/i, { selector: 'small.muted' })).toBeInTheDocument();
    expect(screen.getByText(/Sunucu onerileri getirilemedi/i)).toBeInTheDocument();
  });
});
