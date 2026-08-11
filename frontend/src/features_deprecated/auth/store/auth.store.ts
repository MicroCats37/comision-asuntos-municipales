"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { MeResponse } from "../schemas/auth.types";

/**
 * Authenticated user state.
 */
interface AuthState {
  user: MeResponse | null;
  isAuthenticated: boolean;
  setAuth: (user: MeResponse) => void;
  logout: () => void;
}

/**
 * Store for authenticated user state.
 * Persists only `user` to localStorage — `isAuthenticated` is derived from `user`.
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setAuth: (user) => set({ user, isAuthenticated: true }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    {
      name: "auth-storage",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ user: state.user }),
    },
  ),
);
