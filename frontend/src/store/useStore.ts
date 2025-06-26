import { create } from 'zustand';

interface AppState {
  collection: string | null;
  setCollection: (name: string | null) => void;
}

export const useStore = create<AppState>((set) => ({
  collection: null,
  setCollection: (name) => set({ collection: name || null }),
}));
