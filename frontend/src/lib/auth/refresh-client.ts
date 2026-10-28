import { getCookie, setCookie } from "cookies-next";
import {
  AUTH_COOKIES,
  accessTokenCookieOptions,
  expiresAtCookieOptions,
  refreshTokenCookieOptions,
} from "./cookies";

export interface RefreshResult {
  access_token: string;
  expires_at: string;
}

interface RefreshDependencies {
  fetcher?: typeof fetch;
  readCookie?: typeof getCookie;
  writeCookie?: typeof setCookie;
  apiUrl?: string;
}

export function buildPublicApiUrl(
  path: string,
  apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
): string {
  return `${apiUrl.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

export function getJwtExpiresAt(token: string): string {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("Access token is not a valid JWT");

  try {
    const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const payload = JSON.parse(atob(padded)) as { exp?: unknown };
    if (typeof payload.exp !== "number" || !Number.isFinite(payload.exp)) {
      throw new Error("Access token has no valid exp claim");
    }
    return new Date(payload.exp * 1000).toISOString();
  } catch (error) {
    if (error instanceof Error && error.message.includes("exp claim")) {
      throw error;
    }
    throw new Error("Access token contains an invalid JWT payload");
  }
}

export async function requestTokenRefresh(
  dependencies: RefreshDependencies = {},
): Promise<RefreshResult> {
  const fetcher = dependencies.fetcher ?? fetch;
  const readCookie = dependencies.readCookie ?? getCookie;
  const writeCookie = dependencies.writeCookie ?? setCookie;
  const refreshToken = readCookie(AUTH_COOKIES.REFRESH_TOKEN);

  if (typeof refreshToken !== "string" || !refreshToken) {
    throw new Error("Refresh token not found");
  }

  const response = await fetcher(
    buildPublicApiUrl("token/refresh", dependencies.apiUrl),
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    },
  );

  if (!response.ok) throw new Error("Refresh failed");

  const data = (await response.json()) as {
    access?: string;
    refresh?: string;
  };
  if (!data.access) throw new Error("Access token not returned");

  const expiresAt = getJwtExpiresAt(data.access);
  writeCookie(
    AUTH_COOKIES.ACCESS_TOKEN,
    data.access,
    accessTokenCookieOptions,
  );
  if (data.refresh) {
    writeCookie(
      AUTH_COOKIES.REFRESH_TOKEN,
      data.refresh,
      refreshTokenCookieOptions,
    );
  }
  writeCookie(AUTH_COOKIES.EXPIRES_AT, expiresAt, expiresAtCookieOptions);

  return { access_token: data.access, expires_at: expiresAt };
}
