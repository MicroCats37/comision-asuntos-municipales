import { deleteCookie, getCookie } from "cookies-next";
import { AUTH_COOKIES, AUTH_STORAGE_PREFIX } from "./cookies";
import { buildPublicApiUrl } from "./refresh-client";

interface SessionEndDependencies {
  requestLogout?: () => Promise<unknown>;
  removeCookie?: typeof deleteCookie;
  storage?: Pick<Storage, "removeItem">;
  location?: Pick<Location, "pathname" | "replace">;
}

let sessionEndPromise: Promise<void> | null = null;

async function revokeAndClearServerSession(): Promise<void> {
  const refreshToken = getCookie(AUTH_COOKIES.REFRESH_TOKEN);
  if (typeof refreshToken === "string" && refreshToken) {
    try {
      await fetch(buildPublicApiUrl("token/blacklist"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refreshToken }),
      });
    } catch {
      // Local cleanup still proceeds when backend revocation is unavailable.
    }
  }
  await fetch("/api/auth/logout", { method: "POST" });
}

export function isLoginOrAuthPath(pathname: string): boolean {
  return pathname === "/login" || pathname.startsWith("/api/auth/");
}

export function clearAuthSessionAndRedirect(
  dependencies: SessionEndDependencies = {},
): Promise<void> {
  if (sessionEndPromise) return sessionEndPromise;

  sessionEndPromise = (async () => {
    const requestLogout =
      dependencies.requestLogout ?? revokeAndClearServerSession;
    const removeCookie = dependencies.removeCookie ?? deleteCookie;
    const storage =
      dependencies.storage ??
      (typeof window === "undefined" ? undefined : window.localStorage);
    const location =
      dependencies.location ??
      (typeof window === "undefined" ? undefined : window.location);

    try {
      await requestLogout();
    } catch {
      // Local cleanup still guarantees that the dead session cannot linger.
    }

    for (const cookieName of Object.values(AUTH_COOKIES)) {
      removeCookie(cookieName, { path: "/" });
    }
    storage?.removeItem(`${AUTH_STORAGE_PREFIX}-auth-storage`);

    if (location && !isLoginOrAuthPath(location.pathname)) {
      location.replace("/login");
    }
  })();

  return sessionEndPromise;
}
