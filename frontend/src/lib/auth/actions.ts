"use server";

import { cookies } from "next/headers";
import type { MeResponse } from "@/features/auth/schemas";
import {
  AUTH_COOKIES,
  accessTokenCookieOptions,
  expiresAtCookieOptions,
  refreshTokenCookieOptions,
  userSessionCookieOptions,
} from "./cookies";

/**
 * Set auth cookies from login tokens + user data.
 * Called from server action after successful login.
 */
export async function setAuthCookies(
  accessToken: string,
  refreshToken: string,
  expiresAt: string,
  user: MeResponse,
): Promise<void> {
  const cookieStore = await cookies();

  cookieStore.set(
    AUTH_COOKIES.ACCESS_TOKEN,
    accessToken,
    accessTokenCookieOptions,
  );
  cookieStore.set(
    AUTH_COOKIES.REFRESH_TOKEN,
    refreshToken,
    refreshTokenCookieOptions,
  );
  cookieStore.set(AUTH_COOKIES.EXPIRES_AT, expiresAt, expiresAtCookieOptions);
  cookieStore.set(
    AUTH_COOKIES.USER_SESSION,
    JSON.stringify(user),
    userSessionCookieOptions,
  );
}

/**
 * Clear all auth cookies on logout.
 */
export async function clearAuthCookies(): Promise<void> {
  const cookieStore = await cookies();

  cookieStore.delete(AUTH_COOKIES.ACCESS_TOKEN);
  cookieStore.delete(AUTH_COOKIES.REFRESH_TOKEN);
  cookieStore.delete(AUTH_COOKIES.EXPIRES_AT);
  cookieStore.delete(AUTH_COOKIES.USER_SESSION);
}

/**
 * Get the access token from cookies (server-side only).
 */
export async function getAccessToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIES.ACCESS_TOKEN)?.value ?? null;
}

/**
 * Get the refresh token from cookies (server-side only).
 */
export async function getRefreshToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIES.REFRESH_TOKEN)?.value ?? null;
}

/**
 * Get the access token expiry from cookies (server-side only).
 */
export async function getExpiresAt(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIES.EXPIRES_AT)?.value ?? null;
}

/**
 * Get the user session from cookies (server-side only).
 */
export async function getUserSession(): Promise<MeResponse | null> {
  const cookieStore = await cookies();
  const raw = cookieStore.get(AUTH_COOKIES.USER_SESSION)?.value;
  if (!raw) return null;
  try {
    return JSON.parse(raw) as MeResponse;
  } catch {
    return null;
  }
}

/**
 * Get Authorization header value for API calls.
 */
export async function getAuthHeader(): Promise<string | null> {
  const token = await getAccessToken();
  return token ? `Bearer ${token}` : null;
}
