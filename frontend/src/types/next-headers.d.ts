declare module "next/headers" {
  import type { ReadonlyRequestCookies } from "next/dist/server/web/spec-extension/adapters/request-cookies";

  export function cookies(): Promise<ReadonlyRequestCookies>;
}
