import { create } from 'zustand';
import type { NodeResponse, NodeType } from '../types';

type ModalState =
  | null
  | {
      mode: 'create';
      nodeType: NodeType;
    }
  | {
      mode: 'edit';
      nodeType: NodeType;
      node: NodeResponse;
    };

interface UiState {
  nodeModal: ModalState;
  openCreateModal: (nodeType: NodeType) => void;
  openEditModal: (node: NodeResponse) => void;
  closeModal: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  nodeModal: null,
  openCreateModal: (nodeType) => set({ nodeModal: { mode: 'create', nodeType } }),
  openEditModal: (node) => set({ nodeModal: { mode: 'edit', nodeType: node.type, node } }),
  closeModal: () => set({ nodeModal: null }),
}));
