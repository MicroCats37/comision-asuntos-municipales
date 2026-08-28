"use server";

import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import {
  AUTH_COOKIES,
  accessTokenCookieOptions,
  expiresAtCookieOptions,
  refreshTokenCookieOptions,
} from "@/lib/auth";

/**
 * Refresh access token using the httpOnly refresh cookie.
 *
 * This route handler exists to proxy the backend refresh call from the client.
 * It reads the refresh token from cookies, calls the backend /api/token/refresh
 * endpoint, and sets the rotated tokens as cookies (non-httpOnly for client access).
 *
 * Backend access token lifetime: base 1h, dev override 30d.
 * Djangon-ninja-jwt refresh response doesn't include expires_at,
 * so we compute a generous 30-day fallback to cover all environments.
 */
export async function POST() {
  try {
    const cookieStore = await cookies();

    const refreshToken = cookieStore.get(AUTH_COOKIES.REFRESH_TOKEN)?.value;

    if (!refreshToken) {
      return NextResponse.json(
        { success: false, error: { message: "Refresh token no encontrado" } },
        { status: 401 },
      );
    }

    const backendUrl =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

    // Call backend refresh endpoint
    const response = await fetch(`${backendUrl}/token/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!response.ok) {
      return NextResponse.json(
        { success: false, error: { message: "Refresh fallido" } },
        { status: 401 },
      );
    }

    const data = (await response.json()) as {
      access?: string;
      refresh?: string;
    };

    if (!data.access) {
      return NextResponse.json(
        { success: false, error: { message: "Token de acceso no recibido" } },
        { status: 500 },
      );
    }

    // Compute expires_at fallback: generous match for dev (30d) and prod (1h).
    // Backend base: ACCESS_TOKEN_LIFETIME=1h, dev override: 30d.
    // Djangon-ninja-jwt refresh doesn't return expires_at, so we use a safe upper bound.
    const expiresAt = new Date(
      Date.now() + 30 * 24 * 60 * 60 * 1000,
    ).toISOString();

    // Set rotated tokens as httpOnly cookies
    cookieStore.set(
      AUTH_COOKIES.ACCESS_TOKEN,
      data.access,
      accessTokenCookieOptions,
    );

    if (data.refresh) {
      // ROTATE_REFRESH_TOKENS=True: new refresh token provided, persist it
      cookieStore.set(
        AUTH_COOKIES.REFRESH_TOKEN,
        data.refresh,
        refreshTokenCookieOptions,
      );
    }

    // Set non-httpOnly expires_at for client-side expiry checks
    cookieStore.set(AUTH_COOKIES.EXPIRES_AT, expiresAt, expiresAtCookieOptions);

    return NextResponse.json({
      success: true,
      data: { expires_at: expiresAt },
    });
  } catch {
    return NextResponse.json(
      { success: false, error: { message: "Error interno del servidor" } },
      { status: 500 },
    );
  }
}
