import { create } from 'zustand';
import type { NodeResponse } from '../types';

interface SelectionState {
  selectedNode: NodeResponse | null;
  panelTab: 'details' | 'ai';
  selectNode: (node: NodeResponse | null) => void;
  setPanelTab: (tab: 'details' | 'ai') => void;
}

export const useSelectionStore = create<SelectionState>((set) => ({
  selectedNode: null,
  panelTab: 'details',
  selectNode: (node) => set({ selectedNode: node }),
  setPanelTab: (tab) => set({ panelTab: tab }),
}));
