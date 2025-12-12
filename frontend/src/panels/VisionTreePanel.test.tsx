import '@testing-library/jest-dom';
import { describe, it, vi, beforeEach, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { VisionTreePanel } from './VisionTreePanel';
import { useAuthStore } from '../store/authStore';
import { useSelectionStore } from '../store/selectionStore';
import { useRefreshStore } from '../store/dataRefreshStore';
import { NODE_TYPES } from '../types';
import { moveGoal } from '../api/client';

vi.mock('../hooks/useVisionTree', () => ({
  useVisionTree: () => ({
    data: {
      visions: [
        {
          vision: { id: 'vision-1', type: NODE_TYPES.VISION, name: 'Vision 1' },
          goals: [
            {
              goal: { id: 'goal-1', type: NODE_TYPES.GOAL, name: 'Goal 1' },
              projects: [{ id: 'project-1', type: NODE_TYPES.PROJECT, name: 'Project 1' }],
            },
          ],
        },
        {
          vision: { id: 'vision-2', type: NODE_TYPES.VISION, name: 'Vision 2' },
          goals: [],
        },
      ],
    },
    loading: false,
    error: null,
  }),
}));

vi.mock('../api/client', () => ({
  moveGoal: vi.fn(() => Promise.resolve()),
  moveProject: vi.fn(() => Promise.resolve()),
}));

function enableAuth() {
  useAuthStore.setState({
    token: 'token',
    email: 'drag@test.com',
    loading: false,
    error: null,
    login: async () => {},
    logout: () => {},
  });
}

describe('VisionTreePanel drag and drop', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    enableAuth();
    useSelectionStore.setState({ selectedNode: null, panelTab: 'details', selectNode: () => {}, setPanelTab: () => {} });
    useRefreshStore.setState({
      graphKey: 0,
      visionKey: 0,
      triggerGraphRefresh: () => useRefreshStore.setState((state) => ({ graphKey: state.graphKey + 1 })),
      triggerVisionRefresh: () => useRefreshStore.setState((state) => ({ visionKey: state.visionKey + 1 })),
    });
  });

  it('shows status message after moving goal', async () => {
    render(<VisionTreePanel />);

    const goalButton = screen.getByRole('button', { name: /Goal 1/i });
    fireEvent.dragStart(goalButton);

    const vision2 = screen.getByTestId('vision-vision-2');
    fireEvent.dragOver(vision2!);
    fireEvent.drop(vision2!);

    await waitFor(() => {
      expect(screen.getByText(/Hedef yeni vision altına taşındı/i)).toBeInTheDocument();
      expect(moveGoal).toHaveBeenCalledWith('goal-1', 'vision-2', 0);
    });
  });
});
