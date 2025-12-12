import { create } from 'zustand';

interface RefreshState {
  graphKey: number;
  visionKey: number;
  triggerGraphRefresh: () => void;
  triggerVisionRefresh: () => void;
}

export const useRefreshStore = create<RefreshState>((set) => ({
  graphKey: 0,
  visionKey: 0,
  triggerGraphRefresh: () => set((state) => ({ graphKey: state.graphKey + 1 })),
  triggerVisionRefresh: () => set((state) => ({ visionKey: state.visionKey + 1 })),
}));
