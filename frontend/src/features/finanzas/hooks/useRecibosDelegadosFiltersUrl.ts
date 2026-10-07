"use client";

import { useUrlFilters } from "@/hooks/system/useUrlFilters";

/**
 * URL-driven filter state for RecibosDelegados listing.
 *
 * Thin wrapper around generic `useUrlFilters` hook.
 * Backend filters: delegado_cip (string), municipalidad_id (UUID), periodo (int), mes (int).
 *
 * URL params use the same name as the backend query param
 * for direct compatibility.
 */
export function useRecibosDelegadosFiltersUrl(): {
  filtros: {
    delegado_cip?: string;
    municipalidad_id?: string;
    periodo?: number;
    mes?: number;
  };
  setFiltros: (next: {
    delegado_cip?: string;
    municipalidad_id?: string;
    periodo?: number;
    mes?: number;
  }) => void;
  clearFiltros: () => void;
} {
  const { filtros, setFiltros, clearFiltros } = useUrlFilters<{
    delegado_cip?: string;
    municipalidad_id?: string;
    periodo?: number;
    mes?: number;
  }>({
    config: [
      { filterKey: "delegado_cip", paramKey: "delegado_cip" },
      { filterKey: "municipalidad_id", paramKey: "municipalidad_id" },
      { filterKey: "periodo", paramKey: "periodo", parse: (v) => parseInt(v, 10) },
      { filterKey: "mes", paramKey: "mes", parse: (v) => parseInt(v, 10) },
    ],
    numberKeys: new Set(["periodo", "mes"]),
  });

  return {
    filtros: filtros as {
      delegado_cip?: string;
      municipalidad_id?: string;
      periodo?: number;
      mes?: number;
    },
    setFiltros,
    clearFiltros,
  };
}
