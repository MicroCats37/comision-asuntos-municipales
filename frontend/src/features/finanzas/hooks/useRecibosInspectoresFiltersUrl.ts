"use client";

import { useUrlFilters } from "@/hooks/system/useUrlFilters";

/**
 * URL-driven filter state for RecibosInspectores listing.
 *
 * Thin wrapper around generic `useUrlFilters` hook.
 * Backend filters: inspector_cip (string), periodo (int), mes (int).
 *
 * Mismos filtros que el listado de Delegados, para que ambos listados de RH
 * mensual se comporten igual.
 *
 * URL params use the same name as the backend query param
 * for direct compatibility.
 */
export function useRecibosInspectoresFiltersUrl(): {
  filtros: {
    inspector_cip?: string;
    periodo?: number;
    mes?: number;
  };
  setFiltros: (next: {
    inspector_cip?: string;
    periodo?: number;
    mes?: number;
  }) => void;
  clearFiltros: () => void;
} {
  const { filtros, setFiltros, clearFiltros } = useUrlFilters<{
    inspector_cip?: string;
    periodo?: number;
    mes?: number;
  }>({
    config: [
      { filterKey: "inspector_cip", paramKey: "inspector_cip" },
      {
        filterKey: "periodo",
        paramKey: "periodo",
        parse: (v) => parseInt(v, 10),
      },
      { filterKey: "mes", paramKey: "mes", parse: (v) => parseInt(v, 10) },
    ],
    numberKeys: new Set(["periodo", "mes"]),
  });

  return {
    filtros: filtros as {
      inspector_cip?: string;
      periodo?: number;
      mes?: number;
    },
    setFiltros,
    clearFiltros,
  };
}
