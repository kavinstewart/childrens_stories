/**
 * Zustand store for authentication state.
 * Manages token state and hydration from persistent storage.
 */

import { create } from 'zustand';
import { authStorage } from '@/lib/auth-storage';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  isHydrated: boolean;

  // Actions
  setToken: (token: string) => Promise<void>;
  clearToken: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  isAuthenticated: false,
  isHydrated: false,

  setToken: async (token: string) => {
    await authStorage.setToken(token);
    set({ token, isAuthenticated: true });
  },

  clearToken: async () => {
    await authStorage.clearToken();
    set({ token: null, isAuthenticated: false });
  },

  hydrate: async () => {
    // Skip if already hydrated
    if (get().isHydrated) return;

    const token = await authStorage.getToken();
    set({
      token,
      isAuthenticated: token !== null,
      isHydrated: true,
    });
  },
}));
