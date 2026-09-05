import axios from "axios";
import { getCookie } from "cookies-next";
import { AUTH_COOKIES } from "./auth";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
  timeout: 15000,
});

/**
 * Token refresh state to avoid concurrent refresh attempts.
 * A single refresh promise is shared across all concurrent requests.
 */
let refreshPromise: Promise<{ expires_at: string }> | null = null;

/**
 * Refresh access token via the Next.js server route.
 * Client JS cannot read httpOnly refresh cookie, so we route through /api/auth/refresh.
 * ROTATE_REFRESH_TOKENS=True: backend may return a new refresh token in response,
 * which the server route persists as an httpOnly cookie.
 *
 * Backend access token default lifetime is 1 hour (3600s). When refresh response
 * lacks expires_at, server route uses current time + 1h as a conservative fallback.
 */
async function refreshAccessToken(): Promise<{ expires_at: string }> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const response = await fetch("/api/auth/refresh", { method: "POST" });

    if (!response.ok) {
      refreshPromise = null;
      throw new Error("Refresh failed");
    }

    const data = (await response.json()) as {
      success: boolean;
      data?: { expires_at: string };
      error?: { message: string };
    };

    if (!data.success || !data.data) {
      refreshPromise = null;
      throw new Error(data.error?.message ?? "Refresh failed");
    }

    return { expires_at: data.data.expires_at };
  })();

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
    let token: string | null = null;

    if (typeof window === "undefined") {
      // Server-side: read from httpOnly cookies via cookies-next (synchronous)
      const cookieValue = getCookie(AUTH_COOKIES.ACCESS_TOKEN);
      token = typeof cookieValue === "string" ? cookieValue : null;
    } else {
      // Client-side: read from httpOnly cookie via cookies-next
      const cookieValue = getCookie(AUTH_COOKIES.ACCESS_TOKEN);
      token = typeof cookieValue === "string" ? cookieValue : null;

      // Proactively refresh if token is expiring within 5 minutes
      if (token && isTokenExpiringSoon()) {
        try {
          await refreshAccessToken();
          // After refresh, re-read the new token from cookie
          const newToken = getCookie(AUTH_COOKIES.ACCESS_TOKEN);
          token = typeof newToken === "string" ? newToken : null;
        } catch {
          // Refresh failed; proceed with existing token (may result in 401)
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

    // Only intercept 401 errors for requests that haven't been retried
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;

      try {
        await refreshAccessToken();

        // After successful refresh, retry the original request with new token
        const newToken = getCookie(AUTH_COOKIES.ACCESS_TOKEN);
        if (newToken && typeof newToken === "string") {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
        }

        return api(originalRequest);
      } catch {
        // Refresh failed — let the original 401 error propagate
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  },
);

export default api;
