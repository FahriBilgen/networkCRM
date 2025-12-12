import { create } from 'zustand';
import { mockGraphResponse } from '../mock/data';
import type { FavoritePathResponse, GraphResponse } from '../types';

interface GraphState {
  graph: GraphResponse;
  filteredNodeIds: string[] | null;
  highlightPathNodeIds: string[] | null;
  favoritePaths: FavoritePathResponse[];
  favoritePathsLoaded: boolean;
  setGraph: (graph: GraphResponse) => void;
  setFilteredNodeIds: (ids: string[] | null) => void;
  clearFilteredNodeIds: () => void;
  setHighlightPath: (ids: string[] | null) => void;
  clearHighlightPath: () => void;
  setFavoritePaths: (favorites: FavoritePathResponse[]) => void;
  addFavoritePath: (favorite: FavoritePathResponse) => void;
  removeFavoritePath: (id: string) => void;
  setFavoritePathsLoaded: (loaded: boolean) => void;
  applyFavoritePath: (id: string) => void;
}

export const useGraphStore = create<GraphState>((set, get) => ({
  graph: mockGraphResponse,
  filteredNodeIds: null,
  highlightPathNodeIds: null,
  favoritePaths: [],
  favoritePathsLoaded: false,
  setGraph: (graph) => set({ graph }),
  setFilteredNodeIds: (ids) => set({ filteredNodeIds: ids }),
  clearFilteredNodeIds: () => set({ filteredNodeIds: null }),
  setHighlightPath: (ids) => set({ highlightPathNodeIds: ids }),
  clearHighlightPath: () => set({ highlightPathNodeIds: null }),
  setFavoritePaths: (favorites) => set({ favoritePaths: favorites }),
  addFavoritePath: (favorite) =>
    set((state) => ({
      favoritePaths: [...state.favoritePaths, favorite],
    })),
  removeFavoritePath: (id) =>
    set((state) => ({
      favoritePaths: state.favoritePaths.filter((fav) => fav.id !== id),
    })),
  setFavoritePathsLoaded: (loaded) => set({ favoritePathsLoaded: loaded }),
  applyFavoritePath: (id) => {
    const target = get().favoritePaths.find((fav) => fav.id === id);
    if (target) {
      set({ highlightPathNodeIds: target.nodeIds });
    }
  },
}));
