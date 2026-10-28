/**
 * Auth storage prefix — configurable per environment via NEXT_PUBLIC_AUTH_STORAGE_PREFIX.
 * Default "cam_auth" provides environment isolation for cookies and localStorage.
 */
export const AUTH_STORAGE_PREFIX =
  process.env.NEXT_PUBLIC_AUTH_STORAGE_PREFIX ?? "cam_auth";

/**
 * Cookie configuration constants.
 * All cookies are non-httpOnly: set via cookies-next client-side
 * and read by both client (getCookie) and server (cookies()).
 */
export const AUTH_COOKIES = {
  ACCESS_TOKEN: `${AUTH_STORAGE_PREFIX}_access_token`,
  REFRESH_TOKEN: `${AUTH_STORAGE_PREFIX}_refresh_token`,
  EXPIRES_AT: `${AUTH_STORAGE_PREFIX}_expires_at`,
  USER_SESSION: `${AUTH_STORAGE_PREFIX}_user_session`,
} as const;

export const COOKIE_OPTIONS = {
  httpOnly: false,
  secure: process.env.NEXT_PUBLIC_COOKIE_SECURE === "true",
  sameSite: "lax" as const,
  path: "/",
};

export const ACCESS_TOKEN_MAX_AGE = 12 * 60 * 60;
export const REFRESH_TOKEN_MAX_AGE = 30 * 24 * 60 * 60;

/** Access token cookie */
export const accessTokenCookieOptions = {
  ...COOKIE_OPTIONS,
  maxAge: ACCESS_TOKEN_MAX_AGE,
};

/** Refresh token cookie */
export const refreshTokenCookieOptions = {
  ...COOKIE_OPTIONS,
  maxAge: REFRESH_TOKEN_MAX_AGE,
};

/** Access token expiry — client-readable for proactive refresh checks */
export const expiresAtCookieOptions = {
  ...COOKIE_OPTIONS,
  maxAge: ACCESS_TOKEN_MAX_AGE,
};

/** User session cookie for client hydration */
export const userSessionCookieOptions = {
  ...COOKIE_OPTIONS,
  maxAge: REFRESH_TOKEN_MAX_AGE,
};
