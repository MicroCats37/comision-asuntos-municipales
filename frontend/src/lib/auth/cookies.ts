/**
 * Cookie configuration constants.
 * All cookies are non-httpOnly: set via cookies-next client-side
 * and read by both client (getCookie) and server (cookies()).
 */
export const AUTH_COOKIES = {
  ACCESS_TOKEN: "auth_access_token",
  REFRESH_TOKEN: "auth_refresh_token",
  EXPIRES_AT: "auth_expires_at",
  USER_SESSION: "auth_user_session",
} as const;

export const COOKIE_OPTIONS = {
  httpOnly: false,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/",
};

/** Access token cookie — same lifetime as refresh for consistency */
export const accessTokenCookieOptions = {
  ...COOKIE_OPTIONS,
  maxAge: 30 * 24 * 60 * 60, // 30 days
};

/** Refresh token cookie */
export const refreshTokenCookieOptions = {
  ...COOKIE_OPTIONS,
  maxAge: 7 * 24 * 60 * 60, // 7 days
};

/** Access token expiry — client-readable for proactive refresh checks */
export const expiresAtCookieOptions = {
  ...COOKIE_OPTIONS,
  maxAge: 7 * 24 * 60 * 60,
};

/** User session cookie for client hydration */
export const userSessionCookieOptions = {
  ...COOKIE_OPTIONS,
  maxAge: 7 * 24 * 60 * 60,
};
