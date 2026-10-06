"use client";

import { useUrlFilters } from "@/hooks/system/useUrlFilters";
import type { DelegadoFiltros } from "../types/delegados.types";

/**
 * URL-driven filter state for Delegados listing.
 *
 * Thin wrapper around generic `useUrlFilters` hook.
 * Maintains the existing backend filter contract:
 *   cip, municipalidad_id, capitulo_id, especialidad_id, estado
 *
 * URL params use the same names as the backend query params
 * for direct compatibility (no short-key mapping needed).
 */
export function useDelegadosFiltersUrl(): {
  filtros: Partial<DelegadoFiltros>;
  setFiltros: (next: Partial<DelegadoFiltros>) => void;
  clearFiltros: () => void;
} {
  const { filtros, setFiltros, clearFiltros } = useUrlFilters<DelegadoFiltros>({
    config: [
      { filterKey: "cip", paramKey: "cip" },
      { filterKey: "municipalidad_id", paramKey: "municipalidad_id" },
      { filterKey: "capitulo_id", paramKey: "capitulo_id" },
      { filterKey: "especialidad_id", paramKey: "especialidad_id" },
      { filterKey: "estado", paramKey: "estado" },
    ],
    // All filter keys are string-typed; no number parsing needed.
  });

  return {
    filtros: filtros as Partial<DelegadoFiltros>,
    setFiltros,
    clearFiltros,
  };
}
