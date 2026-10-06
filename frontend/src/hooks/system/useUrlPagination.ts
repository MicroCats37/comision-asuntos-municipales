"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { useUrlSearchParam } from "./useUrlSearchParam";

export const PAGINATION_PAGE_SIZES = [10, 20, 50, 100] as const;
export const PAGINATION_DEFAULTS = { page: 1, pageSize: 20 } as const;

const parsePageParam = (raw: string | null): number => {
  if (!raw) return PAGINATION_DEFAULTS.page;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) && n > 0 ? n : PAGINATION_DEFAULTS.page;
};

const parsePageSizeParam = (raw: string | null): number => {
  if (!raw) return PAGINATION_DEFAULTS.pageSize;
  const n = Number.parseInt(raw, 10);
  return (PAGINATION_PAGE_SIZES as readonly number[]).includes(n)
    ? n
    : PAGINATION_DEFAULTS.pageSize;
};

/**
 * URL-driven pagination state. Page number pushes a history entry (so back
 * returns to the previous page); page size replaces silently (preference, not
 * navigation).
 */
export function useUrlPagination() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [page, setPageRaw] = useUrlSearchParam<number>("page", {
    defaultValue: PAGINATION_DEFAULTS.page,
    parse: parsePageParam,
    mode: "push",
  });
  const [pageSize] = useUrlSearchParam<number>("pageSize", {
    defaultValue: PAGINATION_DEFAULTS.pageSize,
    parse: parsePageSizeParam,
    mode: "replace",
  });

  const setPage = useCallback(
    (next: number | ((prev: number) => number)) => {
      setPageRaw(next);
    },
    [setPageRaw],
  );

  const setPageSize = useCallback(
    (next: number | ((prev: number) => number)) => {
      const resolved =
        typeof next === "function"
          ? (next as (prev: number) => number)(pageSize)
          : next;
      const params = new URLSearchParams(searchParams.toString());

      if (
        Object.is(resolved, PAGINATION_DEFAULTS.pageSize) ||
        !(PAGINATION_PAGE_SIZES as readonly number[]).includes(resolved)
      ) {
        params.delete("pageSize");
      } else {
        params.set("pageSize", String(resolved));
      }

      // Page size changes always reset the list to page 1.
      params.delete("page");

      const qs = params.toString();
      const href = qs ? `${pathname}?${qs}` : pathname;
      router.replace(href, { scroll: false });
    },
    [pageSize, searchParams, pathname, router],
  );

  const resetPagination = useCallback(() => {
    setPageRaw(PAGINATION_DEFAULTS.page);
  }, [setPageRaw]);

  return { page, pageSize, setPage, setPageSize, resetPagination } as const;
}
