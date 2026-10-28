import { describe, expect, it, vi } from "vitest";
import { AUTH_COOKIES } from "./cookies";
import {
  buildPublicApiUrl,
  getJwtExpiresAt,
  requestTokenRefresh,
} from "./refresh-client";

function jwtWithExpiration(exp: number): string {
  const payload = btoa(JSON.stringify({ exp }))
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
  return `header.${payload}.signature`;
}

describe("refresh client", () => {
  it("uses the existing browser API route", () => {
    expect(buildPublicApiUrl("token/refresh", "/backend")).toBe(
      "/backend/token/refresh",
    );
  });

  it("reads the real expiration from the access token", () => {
    expect(getJwtExpiresAt(jwtWithExpiration(1_800_000_000))).toBe(
      new Date(1_800_000_000 * 1000).toISOString(),
    );
  });

  it("persists access, rotated refresh and expiration", async () => {
    const access = jwtWithExpiration(1_800_000_000);
    const writeCookie = vi.fn();
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ access, refresh: "rotated-refresh" }),
    });

    const result = await requestTokenRefresh({
      apiUrl: "/backend",
      fetcher,
      readCookie: vi.fn().mockReturnValue("current-refresh"),
      writeCookie,
    });

    expect(fetcher).toHaveBeenCalledWith(
      "/backend/token/refresh",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ refresh: "current-refresh" }),
      }),
    );
    expect(writeCookie).toHaveBeenCalledWith(
      AUTH_COOKIES.ACCESS_TOKEN,
      access,
      expect.any(Object),
    );
    expect(writeCookie).toHaveBeenCalledWith(
      AUTH_COOKIES.REFRESH_TOKEN,
      "rotated-refresh",
      expect.any(Object),
    );
    expect(result).toEqual({
      access_token: access,
      expires_at: new Date(1_800_000_000 * 1000).toISOString(),
    });
  });
});
