import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();
const setCookie = vi.fn();
const clearAuthSessionAndRedirect = vi.fn();

vi.mock("cookies-next", () => ({ getCookie, setCookie }));
vi.mock("./auth/session-client", () => ({
  clearAuthSessionAndRedirect,
  isLoginOrAuthPath: () => false,
}));

describe("API refresh retry", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    getCookie.mockImplementation((name: string) => {
      if (name.endsWith("expires_at")) {
        return new Date(Date.now() + 60 * 60 * 1000).toISOString();
      }
      if (name.endsWith("refresh_token")) return "old-refresh";
      return "old-access";
    });
  });

  it("single-flights concurrent 401 refreshes and retries with new access", async () => {
    const payload = btoa(JSON.stringify({ exp: 1_900_000_000 }))
      .replace(/=/g, "")
      .replace(/\+/g, "-")
      .replace(/\//g, "_");
    const newAccess = `header.${payload}.signature`;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          access: newAccess,
          refresh: "new-refresh",
        }),
      }),
    );

    const { api } = await import("./api");
    const attempts = new Map<string, number>();
    const authorizationHeaders: unknown[] = [];
    const adapter = vi.fn(async (config) => {
      authorizationHeaders.push(config.headers.Authorization);
      const key = config.url ?? "unknown";
      const attempt = (attempts.get(key) ?? 0) + 1;
      attempts.set(key, attempt);

      if (attempt === 1) {
        return Promise.reject({ config, response: { status: 401 } });
      }

      return {
        data: { ok: true },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    });

    await Promise.all([
      api.get("/protected/one", { adapter }),
      api.get("/protected/two", { adapter }),
    ]);

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(
      authorizationHeaders.filter(
        (header) => header === `Bearer ${newAccess}`,
      ),
    ).toHaveLength(2);
    expect(setCookie).toHaveBeenCalled();
    expect(clearAuthSessionAndRedirect).not.toHaveBeenCalled();
  });
});
