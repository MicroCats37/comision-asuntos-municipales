import axios from "axios";
import { getCookie } from "cookies-next";
import { AUTH_COOKIES } from "./auth";
import {
  clearAuthSessionAndRedirect,
  isLoginOrAuthPath,
} from "./auth/session-client";
import {
  type RefreshResult,
  requestTokenRefresh,
} from "./auth/refresh-client";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
  timeout: 15000,
});

/**
 * Token refresh state to avoid concurrent refresh attempts.
 * A single refresh promise is shared across all concurrent requests.
 */
let refreshPromise: Promise<RefreshResult> | null = null;

/**
 * Refresh directly through the same browser-facing API route used by the
 * application's hooks. The refresh cookie is client-readable by policy.
 */
export async function refreshAccessToken(): Promise<RefreshResult> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = requestTokenRefresh();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

/**
 * Check if the access token is missing or near expiry (within 5 minutes).
 * We read expires_at from a non-httpOnly cookie set during login/refresh.
 */
function isTokenExpiringSoon(): boolean {
  if (typeof window === "undefined") return false;

  try {
    const expiresAt = getCookie(AUTH_COOKIES.EXPIRES_AT);
    if (!expiresAt || typeof expiresAt !== "string") return true;

    const expiryDate = new Date(expiresAt);
    const now = new Date();
    const fiveMinutes = 5 * 60 * 1000;

    return expiryDate.getTime() - now.getTime() < fiveMinutes;
  } catch {
    return true;
  }
}

/**
 * Inject Authorization header from cookies.
 * Uses cookies-next (synchronous API) for both server and client sides.
 */
api.interceptors.request.use(
  async (config) => {
    const retryConfig = config as typeof config & { _retry?: boolean };
    if (retryConfig._retry && config.headers.Authorization) {
      return config;
    }

    let token: string | null = null;

    if (typeof window === "undefined") {
      // Server-side cookie lookup for authenticated API calls.
      const cookieValue = getCookie(AUTH_COOKIES.ACCESS_TOKEN);
      token = typeof cookieValue === "string" ? cookieValue : null;
    } else {
      // Client-side lookup is allowed because auth cookies are readable by policy.
      const cookieValue = getCookie(AUTH_COOKIES.ACCESS_TOKEN);
      token = typeof cookieValue === "string" ? cookieValue : null;

      if (token && isTokenExpiringSoon()) {
        try {
          const refreshed = await refreshAccessToken();
          token = refreshed.access_token;
        } catch {
          await clearAuthSessionAndRedirect();
          throw new Error("Session refresh failed");
        }
      }
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

/**
 * Response interceptor: on 401, attempt refresh once then retry original request.
 * Avoids infinite loops by tracking _retry flag on the config object.
 */
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const requestUrl = originalRequest?.url ?? "";
    const isAuthRequest =
      requestUrl.startsWith("/auth/login") ||
      (typeof window !== "undefined" &&
        isLoginOrAuthPath(window.location.pathname));

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !isAuthRequest &&
      typeof window !== "undefined" &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;

      try {
        const refreshed = await refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${refreshed.access_token}`;

        return api(originalRequest);
      } catch {
        await clearAuthSessionAndRedirect();
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  },
);

export default api;
