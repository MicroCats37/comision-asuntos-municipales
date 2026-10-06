"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import type { ApiResponse } from "@/types/api.types";
import type { MeResponse } from "../schemas/auth.types";
import { useAuthStore } from "../store/auth.store";

/**
 * Client shell that validates the persisted auth token on mount.
 *
 * Pattern: "refresh on mount" — user data from localStorage is shown immediately,
 * and fresh data arrives in the background via GET /auth/me.
 *
 * On 401 (token invalid/expired), clears the store via logout().
 */
export function AuthHydrationShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = useAuthStore((state) => state.user);
  const setAuth = useAuthStore((state) => state.setAuth);
  const logout = useAuthStore((state) => state.logout);

  useEffect(() => {
    // Only run if we have a persisted user (store was rehydrated with data)
    if (!user) return;

    const validateToken = async () => {
      try {
        const response = await api.get<ApiResponse<MeResponse>>("/auth/me");

        if (response.data?.success && response.data?.data) {
          // Token is valid — refresh user data in store
          setAuth(response.data.data);
        } else {
          // 401 or other error — clear invalid session
          logout();
        }
      } catch {
        // Network error or unexpected failure — clear invalid session
        logout();
      }
    };

    validateToken();
  }, [
    // Network error or unexpected failure — clear invalid session
    logout, // Token is valid — refresh user data in store
    setAuth,
    user,
  ]); // eslint-disable-line react-hooks/exhaustive-deps

  return <>{children}</>;
}
