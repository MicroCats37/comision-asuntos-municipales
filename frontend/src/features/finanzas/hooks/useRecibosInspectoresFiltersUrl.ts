"use client";

import { useUrlFilters } from "@/hooks/system/useUrlFilters";

/**
 * URL-driven filter state for RecibosInspectores listing.
 *
 * Thin wrapper around generic `useUrlFilters` hook.
 * Backend filter: inspector_id (UUID)
 *
 * URL params use the same name as the backend query param
 * for direct compatibility.
 */
export function useRecibosInspectoresFiltersUrl(): {
  filtros: { inspector_id?: string };
  setFiltros: (next: { inspector_id?: string }) => void;
  clearFiltros: () => void;
} {
  const { filtros, setFiltros, clearFiltros } = useUrlFilters<{
    inspector_id?: string;
  }>({
    config: [{ filterKey: "inspector_id", paramKey: "inspector_id" }],
  });

  return {
    filtros: filtros as { inspector_id?: string },
    setFiltros,
    clearFiltros,
  };
}
