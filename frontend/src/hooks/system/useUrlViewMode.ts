"use client";

import { useUrlSearchParam } from "./useUrlSearchParam";

export type ViewMode = "cards" | "table";
const VIEW_DEFAULT: ViewMode = "cards";

const parseViewMode = (raw: string | null): ViewMode =>
  raw === "table" ? "table" : VIEW_DEFAULT;

/**
 * URL-driven view-mode toggle. The "cards" default is omitted from the URL —
 * only `?view=table` is written when active. Back/forward naturally restores.
 */
export function useUrlViewMode(key = "view") {
  return useUrlSearchParam<ViewMode>(key, {
    defaultValue: VIEW_DEFAULT,
    parse: parseViewMode,
    mode: "replace",
  });
}
