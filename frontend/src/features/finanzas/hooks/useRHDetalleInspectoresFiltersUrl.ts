"use client";

import { useUrlFilters } from "@/hooks/system/useUrlFilters";

/**
 * URL-driven filter state for RH Detalle Inspectores listing.
 *
 * Thin wrapper around generic `useUrlFilters` hook.
 * Backend filters: inspector_cip (CIP string), periodo (int year), mes (int 1-12),
 * municipalidad_id (UUID), numero_liquidacion (int)
 *
 * URL params use the same name as the backend query params
 * for direct compatibility.
 */
export function useRHDetalleInspectoresFiltersUrl(): {
  filtros: {
    inspector_cip?: string;
    periodo?: number;
    mes?: number;
    municipalidad_id?: string;
    numero_liquidacion?: number;
  };
  setFiltros: (next: {
    inspector_cip?: string;
    periodo?: number;
    mes?: number;
    municipalidad_id?: string;
    numero_liquidacion?: number;
  }) => void;
  clearFiltros: () => void;
} {
  const { filtros, setFiltros, clearFiltros } = useUrlFilters<{
    inspector_cip?: string;
    periodo?: number;
    mes?: number;
    municipalidad_id?: string;
    numero_liquidacion?: number;
  }>({
    config: [
      { filterKey: "inspector_cip", paramKey: "inspector_cip" },
      {
        filterKey: "periodo",
        paramKey: "periodo",
        parse: (v) => parseInt(v, 10),
      },
      { filterKey: "mes", paramKey: "mes", parse: (v) => parseInt(v, 10) },
      { filterKey: "municipalidad_id", paramKey: "municipalidad_id" },
      {
        filterKey: "numero_liquidacion",
        paramKey: "numero_liquidacion",
        parse: (v) => parseInt(v, 10),
      },
    ],
    numberKeys: new Set(["periodo", "mes", "numero_liquidacion"]),
  });

  return {
    filtros: filtros as {
      inspector_cip?: string;
      periodo?: number;
      mes?: number;
      municipalidad_id?: string;
      numero_liquidacion?: number;
    },
    setFiltros,
    clearFiltros,
  };
}
