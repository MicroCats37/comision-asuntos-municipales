"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

/**
 * Configuration for a single filter key:
 * - filterKey: keyof T — the property name in the filter object
 * - paramKey: string — the short URL parameter name
 * - parse: optional custom parser from string to T[K] (default: identity)
 * - serialize: optional custom serializer from T[K] to string (default: String)
 */
export interface UrlFilterConfig<T extends object> {
  filterKey: keyof T;
  paramKey: string;
  parse?: (raw: string) => T[keyof T];
  serialize?: (value: T[keyof T]) => string;
}

/**
 * Configuration for number-typed filter keys that should be parsed as integers.
 * When a key is listed here, parseInt is used to convert the URL value.
 */
export type NumberFilterKeys<T extends object> = ReadonlySet<keyof T>;

const defaultParse = <T>(raw: string): T => raw as T;
const defaultSerialize = (value: unknown): string => String(value);

/**
 * URL-driven filter state hook. Generic over the filter object type T.
 *
 * Features:
 * - Typed filter object (caller-defined)
 * - Caller-provided param key map
 * - Number key parsing support
 * - Empty value omission
 * - Reset `page` when filters change
 * - Single `router.replace` call preserving unrelated params
 *
 * @example
 * ```typescript
 * type MisFiltros = { muni: string; desde: string; num: number };
 *
 * const config: UrlFilterConfig<MisFiltros>[] = [
 *   { filterKey: 'muni', paramKey: 'muni' },
 *   { filterKey: 'desde', paramKey: 'desde' },
 *   { filterKey: 'num', paramKey: 'num', parse: (v) => parseInt(v, 10) },
 * ];
 *
 * const { filtros, setFiltros, clearFiltros } = useUrlFilters({ config });
 * ```
 */
export function useUrlFilters<T extends object>({
  config,
  numberKeys,
}: {
  /** Array of filter configurations mapping filter keys to URL param keys. */
  config: UrlFilterConfig<T>[];
  /** Optional set of keys that should be parsed as numbers (parseInt). */
  numberKeys?: NumberFilterKeys<T>;
}): {
  filtros: Partial<T>;
  setFiltros: (next: Partial<T>) => void;
  clearFiltros: () => void;
} {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Build fast-lookup maps
  const paramKeyToConfig = useMemo(() => {
    const map = new Map<string, UrlFilterConfig<T>>();
    for (const cfg of config) {
      map.set(cfg.paramKey, cfg);
    }
    return map;
  }, [config]);

  /** Parse a single filter value from a URL param string. */
  const parseValue = useCallback(
    (filterKey: keyof T, raw: string): T[keyof T] => {
      // 1. Check if it's a declared number key
      if (numberKeys?.has(filterKey)) {
        const n = Number.parseInt(raw, 10);
        return (Number.isFinite(n) ? n : raw) as T[keyof T];
      }
      // 2. Check if config has a custom parser
      const cfg = paramKeyToConfig.get(filterKey as unknown as string);
      if (cfg?.parse) {
        return cfg.parse(raw);
      }
      // 3. Default: identity
      return defaultParse<T[keyof T]>(raw);
    },
    [numberKeys, paramKeyToConfig],
  );

  /** Serialize a filter value to a URL param string. */
  const serializeValue = useCallback(
    (filterKey: keyof T, value: T[keyof T]): string => {
      const cfg = paramKeyToConfig.get(filterKey as unknown as string);
      if (cfg?.serialize) {
        return cfg.serialize(value);
      }
      return defaultSerialize(value);
    },
    [paramKeyToConfig],
  );

  /** Read filters from current URL search params. */
  const filtros = useMemo<Partial<T>>(() => {
    const next: Partial<T> = {} as Partial<T>;
    for (const [paramKey, cfg] of paramKeyToConfig.entries()) {
      const raw = searchParams.get(paramKey);
      if (raw === null || raw === "") continue;
      (next as Record<string, unknown>)[cfg.filterKey as string] = parseValue(
        cfg.filterKey,
        raw,
      );
    }
    return next;
  }, [searchParams, paramKeyToConfig, parseValue]);

  /** Write filters to URL — replaces all filter params, resets page, single replace. */
  const setFiltros = useCallback(
    (next: Partial<T>) => {
      const params = new URLSearchParams(searchParams.toString());

      // Remove any existing filter params first.
      for (const cfg of config) {
        params.delete(cfg.paramKey);
      }
      // Always reset page when filters change.
      params.delete("page");

      for (const cfg of config) {
        const value = (next as Record<string, unknown>)[
          cfg.filterKey as string
        ];
        if (value === null || value === undefined) continue;
        if (typeof value === "string" && value.trim().length === 0) continue;
        params.set(
          cfg.paramKey,
          serializeValue(cfg.filterKey, value as T[keyof T]),
        );
      }

      const qs = params.toString();
      const href = qs ? `${pathname}?${qs}` : pathname;
      router.replace(href, { scroll: false });
    },
    [config, searchParams, pathname, router, serializeValue],
  );

  const clearFiltros = useCallback(
    () => setFiltros({} as Partial<T>),
    [setFiltros],
  );

  return { filtros, setFiltros, clearFiltros };
}
