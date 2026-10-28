import { describe, expect, it } from "vitest";
import {
  ACCESS_TOKEN_MAX_AGE,
  accessTokenCookieOptions,
  expiresAtCookieOptions,
  REFRESH_TOKEN_MAX_AGE,
  refreshTokenCookieOptions,
  userSessionCookieOptions,
} from "./cookies";

describe("auth cookie lifetimes", () => {
  it("keeps access state for exactly 12 hours", () => {
    expect(ACCESS_TOKEN_MAX_AGE).toBe(12 * 60 * 60);
    expect(accessTokenCookieOptions.maxAge).toBe(ACCESS_TOKEN_MAX_AGE);
    expect(expiresAtCookieOptions.maxAge).toBe(ACCESS_TOKEN_MAX_AGE);
  });

  it("keeps refresh-backed session state for exactly 30 days", () => {
    expect(REFRESH_TOKEN_MAX_AGE).toBe(30 * 24 * 60 * 60);
    expect(refreshTokenCookieOptions.maxAge).toBe(REFRESH_TOKEN_MAX_AGE);
    expect(userSessionCookieOptions.maxAge).toBe(REFRESH_TOKEN_MAX_AGE);
  });

  it("retains client-readable auth cookies by explicit policy", () => {
    expect(accessTokenCookieOptions.httpOnly).toBe(false);
    expect(refreshTokenCookieOptions.httpOnly).toBe(false);
  });
});
