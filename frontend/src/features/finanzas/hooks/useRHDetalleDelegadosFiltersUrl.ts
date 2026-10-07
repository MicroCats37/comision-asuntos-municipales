"use client";

import { useUrlFilters } from "@/hooks/system/useUrlFilters";

/**
 * URL-driven filter state for RH Detalle Delegados listing.
 *
 * Thin wrapper around generic `useUrlFilters` hook.
 * Backend filters: delegado_cip (CIP string), periodo (int year, optional),
 * mes (int 1-12, optional), municipalidad_id (UUID, optional),
 * tipo_liquidacion_codigo (string, REQUIRED), numero_liquidacion (int, optional).
 *
 * URL params use the same name as the backend query params
 * for direct compatibility.
 */
export function useRHDetalleDelegadosFiltersUrl(): {
  filtros: {
    delegado_cip?: string;
    periodo?: number;
    mes?: number;
    municipalidad_id?: string;
    tipo_liquidacion_codigo?: string;
    numero_liquidacion?: number;
  };
  setFiltros: (next: {
    delegado_cip?: string;
    periodo?: number;
    mes?: number;
    municipalidad_id?: string;
    tipo_liquidacion_codigo?: string;
    numero_liquidacion?: number;
  }) => void;
  clearFiltros: () => void;
} {
  const { filtros, setFiltros, clearFiltros } = useUrlFilters<{
    delegado_cip?: string;
    periodo?: number;
    mes?: number;
    municipalidad_id?: string;
    tipo_liquidacion_codigo?: string;
    numero_liquidacion?: number;
  }>({
    config: [
      { filterKey: "delegado_cip", paramKey: "delegado_cip" },
      {
        filterKey: "periodo",
        paramKey: "periodo",
        parse: (v) => parseInt(v, 10),
      },
      { filterKey: "mes", paramKey: "mes", parse: (v) => parseInt(v, 10) },
      { filterKey: "municipalidad_id", paramKey: "municipalidad_id" },
      {
        filterKey: "tipo_liquidacion_codigo",
        paramKey: "tipo_liquidacion_codigo",
      },
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
      delegado_cip?: string;
      periodo?: number;
      mes?: number;
      municipalidad_id?: string;
      tipo_liquidacion_codigo?: string;
      numero_liquidacion?: number;
    },
    setFiltros,
    clearFiltros,
  };
}
