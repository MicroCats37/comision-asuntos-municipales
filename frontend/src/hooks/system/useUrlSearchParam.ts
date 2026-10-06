"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

export type UrlSetMode = "push" | "replace";

export interface UseUrlSearchParamOptions<T> {
  /** Value used when the param is absent or invalid. */
  defaultValue: T;
  /** Parse from raw string. Default: identity. */
  parse?: (raw: string | null) => T;
  /** Serialize to raw string. Default: String(value). */
  serialize?: (value: T) => string;
  /**
   * History write mode. Default: "push" (creates a history entry, enabling
   * browser back/forward). Use "replace" for noisy changes (e.g. pageSize)
   * that would otherwise pollute the back stack.
   */
  mode?: UrlSetMode;
}

const identityParse = <T>(raw: string | null): T => raw as unknown as T;
const identitySerialize = <T>(value: T): string => String(value);

/**
 * Typed read/write of a single URL search param.
 *
 * - Reads via `useSearchParams()`.
 * - Writes via `useRouter().push` (or `replace`) against the current pathname.
 * - Omits the param when the value equals `defaultValue` (or is nullish),
 *   keeping URLs clean (e.g. `?view=` only appears when view is non-default).
 *
 * ⚠️ Requires a `<Suspense>` boundary in Next.js 16 when read inside a Server
 * Component tree. Our `'use client'` views sit inside the page Server Component
 * — wrap consumers in `<Suspense fallback={...}>` at the view boundary.
 */
export function useUrlSearchParam<T>(
  key: string,
  options: UseUrlSearchParamOptions<T>,
): readonly [T, (next: T | ((prev: T) => T)) => void] {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const parse = options.parse ?? identityParse<T>;
  const serialize = options.serialize ?? identitySerialize<T>;
  const defaultValue = options.defaultValue;
  const mode = options.mode ?? "push";

  const value = useMemo(
    () => parse(searchParams.get(key)),
    [searchParams, key, parse],
  );

  const setValue = useCallback(
    (next: T | ((prev: T) => T)) => {
      const resolved =
        typeof next === "function" ? (next as (prev: T) => T)(value) : next;

      const params = new URLSearchParams(searchParams.toString());
      const shouldOmit =
        resolved === null ||
        resolved === undefined ||
        Object.is(resolved, defaultValue);

      if (shouldOmit) {
        params.delete(key);
      } else {
        params.set(key, serialize(resolved));
      }

      const qs = params.toString();
      const href = qs ? `${pathname}?${qs}` : pathname;
      const navigate = mode === "replace" ? router.replace : router.push;
      navigate(href, { scroll: false });
    },
    [searchParams, pathname, router, value, serialize, defaultValue, mode, key],
  );

  return [value, setValue] as const;
}
