"use client";

import { useUrlFilters } from "@/hooks/system/useUrlFilters";
import type { LiquidacionFiltros } from "./useLiquidacionList";

type LiquidacionFilterKey = keyof LiquidacionFiltros;

const FILTER_NUMBER_KEYS: ReadonlySet<LiquidacionFilterKey> = new Set([
  "numero",
  "numero_revisiones",
]);

/**
 * URL-driven filter state for any liquidacion listing. All 6 tipo-specific views
 * share this shape — own the URL, share the contract.
 *
 * - Reading: walks each known filter key, parses from raw.
 * - Writing: replaces the entire filter object in one `router.replace` call,
 *   resetting `?page` so the user lands on page 1 of the new result set.
 * - Empty values are omitted from the URL (e.g. `?prop=` never appears).
 *
 * This is a thin wrapper around the generic `useUrlFilters` hook.
 */
export function useLiquidacionFiltersUrl(): {
  filtros: LiquidacionFiltros;
  setFiltros: (next: LiquidacionFiltros) => void;
  clearFiltros: () => void;
} {
  const { filtros, setFiltros, clearFiltros } =
    useUrlFilters<LiquidacionFiltros>({
      config: [
        { filterKey: "entidad_id", paramKey: "muni" },
        { filterKey: "propietario", paramKey: "prop" },
        { filterKey: "fecha_desde", paramKey: "desde" },
        { filterKey: "fecha_hasta", paramKey: "hasta" },
        { filterKey: "numero", paramKey: "num" },
        { filterKey: "razon_social", paramKey: "rs" },
        { filterKey: "creado_por", paramKey: "creador" },
        { filterKey: "numero_revisiones", paramKey: "rev" },
        { filterKey: "direccion", paramKey: "dir" },
      ],
      numberKeys: FILTER_NUMBER_KEYS,
    });

  return {
    filtros: filtros as LiquidacionFiltros,
    setFiltros,
    clearFiltros,
  };
}
