import { describe, expect, it, vi } from "vitest";
import { AUTH_COOKIES, AUTH_STORAGE_PREFIX } from "./cookies";
import { clearAuthSessionAndRedirect } from "./session-client";

describe("clearAuthSessionAndRedirect", () => {
  it("clears auth state and replaces a protected location with login", async () => {
    const requestLogout = vi.fn().mockRejectedValue(new Error("offline"));
    const removeCookie = vi.fn();
    const storage = { removeItem: vi.fn() };
    const location = { pathname: "/liquidaciones", replace: vi.fn() };

    await clearAuthSessionAndRedirect({
      requestLogout,
      removeCookie,
      storage,
      location,
    });

    expect(removeCookie).toHaveBeenCalledTimes(
      Object.keys(AUTH_COOKIES).length,
    );
    expect(storage.removeItem).toHaveBeenCalledWith(
      `${AUTH_STORAGE_PREFIX}-auth-storage`,
    );
    expect(location.replace).toHaveBeenCalledWith("/login");
  });
});
