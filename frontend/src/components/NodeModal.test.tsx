import '@testing-library/jest-dom';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NodeModal } from './NodeModal';
import { useUiStore } from '../store/uiStore';
import { useRefreshStore } from '../store/dataRefreshStore';
import { createNode, updateNode, suggestNodeSector } from '../api/client';
import { NODE_TYPES } from '../types';
import type { NodeType } from '../types';
import type { Mock } from 'vitest';

vi.mock('../api/client', () => ({
  createNode: vi.fn(() => Promise.resolve({})),
  updateNode: vi.fn(() => Promise.resolve({})),
  classifyNodeCandidate: vi.fn(() =>
    Promise.resolve({
      suggestedType: 'GOAL',
      confidence: 0.5,
      scores: {},
    }),
  ),
  suggestNodeSector: vi.fn(() =>
    Promise.resolve({
      sector: 'AI',
      confidence: 0.6,
      matchedKeywords: ['ai'],
    }),
  ),
}));

describe('NodeModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useUiStore.getState().closeModal();
    useRefreshStore.setState({ graphKey: 0, visionKey: 0 });
  });

  const openModal = (mode: 'create' | 'edit', type: NodeType = NODE_TYPES.PERSON) => {
    const { openCreateModal, openEditModal } = useUiStore.getState();
    if (mode === 'create') {
      openCreateModal(type);
    } else {
      openEditModal({
        id: 'node-1',
        type,
        name: 'Existing',
        sector: 'AI',
        tags: ['mentor'],
        relationshipStrength: 3,
        notes: 'Old note',
      } as any);
    }
  };

  it('submits required person fields with tags and notes', async () => {
    render(<NodeModal />);
    act(() => openModal('create', NODE_TYPES.PERSON));

    fireEvent.change(screen.getByLabelText(/Isim/i), { target: { value: 'Yeni Kisi' } });
    fireEvent.change(screen.getByLabelText(/Sektor/i), { target: { value: 'SaaS' } });
    fireEvent.change(screen.getByLabelText(/Etiketler/i), { target: { value: 'mentor, yatirimci ' } });
    fireEvent.change(screen.getByLabelText(/Iliski Gucu/i), { target: { value: '5' } });
    fireEvent.change(screen.getByLabelText(/Notlar/i), { target: { value: 'Not girildi' } });

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: /Kaydet/ }));
    });

    expect(createNode).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Yeni Kisi',
        sector: 'SaaS',
        tags: ['mentor', 'yatirimci'],
        relationshipStrength: 5,
        notes: 'Not girildi',
      }),
    );

    await waitFor(() => {
      expect(useRefreshStore.getState().graphKey).toBe(1);
      expect(useRefreshStore.getState().visionKey).toBe(1);
    });
  });

  it('submits goal-specific fields when editing', async () => {
    render(<NodeModal />);
    act(() => openModal('edit', NODE_TYPES.GOAL));

    fireEvent.change(screen.getByLabelText(/Isim/i), { target: { value: 'Guncel Hedef' } });
    fireEvent.change(screen.getByLabelText(/Oncelik/i), { target: { value: '5' } });
    fireEvent.change(screen.getByLabelText(/Notlar/i), { target: { value: 'Guncel not' } });

    await act(async () => {
      fireEvent.submit(screen.getByRole('button', { name: /Kaydet/ }));
    });

    expect(updateNode).toHaveBeenCalledWith(
      'node-1',
      expect.objectContaining({
        name: 'Guncel Hedef',
        priority: 5,
        notes: 'Guncel not',
      }),
    );
  });

  it('fetches and applies sector suggestion', async () => {
    render(<NodeModal />);
    act(() => openModal('create', NODE_TYPES.PERSON));

    const suggestionMock = suggestNodeSector as unknown as Mock;
    suggestionMock.mockResolvedValueOnce({
      sector: 'Fintech',
      confidence: 0.82,
      matchedKeywords: ['fintech'],
    });

    fireEvent.change(screen.getByLabelText(/Isim/i), { target: { value: 'Yeni Kisi' } });
    fireEvent.change(screen.getByLabelText(/Aciklama/i), { target: { value: 'Finans uzmani' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Sektor oner/i }));
    });

    await waitFor(() =>
      expect(suggestNodeSector).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Yeni Kisi',
          description: 'Finans uzmani',
        }),
      ),
    );

    await waitFor(() => expect(screen.getByText('Fintech')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Sektoru uygula/i }));
    expect(screen.getByLabelText(/Sektor/i)).toHaveValue('Fintech');
  });
});
