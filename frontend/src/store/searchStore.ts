import { create } from 'zustand';
import { searchNodes } from '../api/client';
import type { NodeResponse } from '../types';

interface SearchState {
  query: string;
  results: NodeResponse[];
  loading: boolean;
  error: string | null;
  search: (value: string) => Promise<void>;
  clear: () => void;
}

export const useSearchStore = create<SearchState>((set) => ({
  query: '',
  results: [],
  loading: false,
  error: null,
  async search(value: string) {
    set({ query: value, loading: true, error: null });
    try {
      const trimmed = value.trim();
      if (!trimmed) {
        set({ results: [], loading: false });
        return;
      }
      const data = await searchNodes(trimmed);
      set({ results: data, loading: false });
    } catch (err) {
      console.warn('Search failed', err);
      set({ error: 'Arama sırasında hata oluştu', loading: false, results: [] });
    }
  },
  clear() {
    set({ query: '', results: [], loading: false, error: null });
  },
}));
