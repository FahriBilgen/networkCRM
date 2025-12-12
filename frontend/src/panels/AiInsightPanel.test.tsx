import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AiInsightPanel } from './AiInsightPanel';
import { useSelectionStore } from '../store/selectionStore';
import { useGraphStore } from '../store/graphStore';
import { EDGE_TYPES, NODE_TYPES } from '../types';

const mockGoalSuggestions = vi.fn(() => Promise.reject(new Error('unavailable')));
const mockGoalDiagnostics = vi.fn(() => Promise.reject(new Error('diag unavailable')));
const mockRelationshipNudges = vi.fn(() => Promise.resolve({ nudges: [] }));

vi.mock('../api/client', () => ({
  fetchGoalSuggestions: (...args: unknown[]) => mockGoalSuggestions(...args),
  fetchGoalDiagnostics: (...args: unknown[]) => mockGoalDiagnostics(...args),
  fetchRelationshipNudges: (...args: unknown[]) => mockRelationshipNudges(...args),
}));

describe('AiInsightPanel fallback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGoalSuggestions.mockImplementation(() => Promise.reject(new Error('unavailable')));
    mockGoalDiagnostics.mockImplementation(() => Promise.reject(new Error('diag unavailable')));
    mockRelationshipNudges.mockResolvedValue({ nudges: [] });
    useGraphStore.setState((state) => ({
      ...state,
      graph: {
        nodes: [
          { id: 'goal-1', type: NODE_TYPES.GOAL, name: 'MVP', description: 'Test goal' },
          { id: 'person-1', type: NODE_TYPES.PERSON, name: 'Ahmet', sector: 'Fintech' },
        ],
        links: [
          {
            id: 'edge-1',
            sourceNodeId: 'person-1',
            targetNodeId: 'goal-1',
            type: EDGE_TYPES.SUPPORTS,
            relevanceScore: 0.82,
          },
        ],
      },
    }));
    useSelectionStore.setState({
      selectedNode: {
        id: 'goal-1',
        type: NODE_TYPES.GOAL,
        name: 'MVP',
      } as any,
      panelTab: 'details',
      selectNode: () => {},
      setPanelTab: () => {},
    });
  });

  it('shows fallback suggestions from graph store when API fails', async () => {
    render(<AiInsightPanel />);
    await waitFor(() => {
      expect(screen.getByText('Ahmet')).toBeInTheDocument();
      expect(screen.getByText(/82%/)).toBeInTheDocument();
    });
    expect(
      screen.getByText((text) => text.toLowerCase().includes('yapay zeka') && text.toLowerCase().includes('mevcut')),
    ).toBeInTheDocument();
  });

  it('renders diagnostics and risk alerts for supports', async () => {
    useGraphStore.setState((state) => ({
      ...state,
      graph: {
        nodes: [
          { id: 'goal-1', type: NODE_TYPES.GOAL, name: 'MVP', description: 'Test goal' },
          { id: 'person-1', type: NODE_TYPES.PERSON, name: 'Ahmet', sector: 'Fintech' },
          { id: 'person-2', type: NODE_TYPES.PERSON, name: 'Deniz', sector: 'Marketing' },
        ],
        links: [
          {
            id: 'edge-1',
            sourceNodeId: 'person-1',
            targetNodeId: 'goal-1',
            type: EDGE_TYPES.SUPPORTS,
            relationshipStrength: 5,
            lastInteractionDate: new Date().toISOString(),
          },
          {
            id: 'edge-2',
            sourceNodeId: 'person-2',
            targetNodeId: 'goal-1',
            type: EDGE_TYPES.SUPPORTS,
            relationshipStrength: 2,
            lastInteractionDate: '2023-01-01',
          },
        ],
      },
    }));

    render(<AiInsightPanel />);
    await screen.findByText(/Ağ Durumu/);

    expect(screen.getByText(/2 bağlantı/i)).toBeInTheDocument();
    expect(screen.getByText(/Risk Uyarıları/)).toBeInTheDocument();
    expect(screen.getByText(/iletişim yok/i)).toBeInTheDocument();
  });

  it('shows relationship nudges from API when available', async () => {
    mockGoalSuggestions.mockResolvedValueOnce({ goalId: 'goal-1', suggestions: [] });
    mockGoalDiagnostics.mockResolvedValueOnce({
      goalId: 'goal-1',
      readiness: { level: 'weak', score: 0.2, message: 'Zayif', summary: [] },
      sectorHighlights: [],
      riskAlerts: [],
    });
    mockRelationshipNudges.mockResolvedValueOnce({
      nudges: [
        {
          person: { id: 'person-3', type: NODE_TYPES.PERSON, name: 'Bora' } as any,
          edgeType: EDGE_TYPES.KNOWS,
          lastInteractionDate: null,
          relationshipStrength: 1,
          targetName: 'Networking',
          reasons: ['100 gündür iletişim yok.'],
        },
      ],
    });

    render(<AiInsightPanel />);
    await screen.findByText(/İlişki Hatırlatmaları/);
    expect(screen.getByText('Bora')).toBeInTheDocument();
    expect(screen.getByText(/100 gündür/)).toBeInTheDocument();
  });
});
