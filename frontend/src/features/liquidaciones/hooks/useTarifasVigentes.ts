/**
 * Hooks para obtener tarifas vigentes de los endpoints GET /tarifas-vigentes.
 * Se usan para alimentar el selector de tarifas en los formularios M2 e Inspección de Obra,
 * reemplazando el input manual de UUID.
 */
import type { z } from "zod";
import { useApiQuery } from "@/hooks";
import {
  tarifasVigentesM2ResponseSchema,
  tarifasVigentesVisitasResponseSchema,
} from "../schemas/liquidacion-no-edificacion.schema";
import type {
  LiquidacionM2Kind,
  TarifaVigenteM2,
  TarifaVigenteVisita,
} from "../types/liquidacion-no-edificacion.types";
import {
  TARIFAS_VIGENTES_ENDPOINTS,
  TARIFA_VIGENTE_ENDPOINT_INSPECCION,
} from "../types/liquidacion-no-edificacion.types";

export interface TarifasVigentesM2Filters {
  tramite_accion?: string;
}

export interface TarifasVigentesInspeccionFilters {
  tramite_accion?: string;
  categoria?: string;
}

/**
 * Hook para obtener tarifas vigentes de liquidaciones M2
 * (Habilitación Urbana, Mecánica de Suelos, Impacto Vial, Taludes).
 *
 * @param kind - Tipo de liquidación M2
 * @param filters - Filtros opcionales (tramite_accion)
 */
export function useTarifasVigentesM2(
  kind: LiquidacionM2Kind,
  filters?: TarifasVigentesM2Filters,
) {
  const endpoint = TARIFAS_VIGENTES_ENDPOINTS[kind];
  const params: Record<string, string> = {};
  if (filters?.tramite_accion) {
    params.tramite_accion = filters.tramite_accion;
  }

  const query = useApiQuery<
    z.infer<typeof tarifasVigentesM2ResponseSchema>,
    TarifaVigenteM2[]
  >({
    queryKey: ["liquidaciones", "tarifas-vigentes", kind, filters?.tramite_accion],
    url: endpoint,
    schema: tarifasVigentesM2ResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) return [] as TarifaVigenteM2[];
        return data.data.tarifas;
      },
    },
  });

  return query;
}

/**
 * Hook para obtener tarifas vigentes de Inspección de Obra.
 *
 * @param filters - Filtros opcionales (tramite_accion, categoria)
 */
export function useTarifasVigentesInspeccionObra(
  filters?: TarifasVigentesInspeccionFilters,
) {
  const params: Record<string, string> = {};
  if (filters?.tramite_accion) {
    params.tramite_accion = filters.tramite_accion;
  }
  if (filters?.categoria) {
    params.categoria = filters.categoria;
  }

  const query = useApiQuery<
    z.infer<typeof tarifasVigentesVisitasResponseSchema>,
    TarifaVigenteVisita[]
  >({
    queryKey: [
      "liquidaciones",
      "tarifas-vigentes",
      "inspeccion-obra",
      filters?.tramite_accion,
      filters?.categoria,
    ],
    url: TARIFA_VIGENTE_ENDPOINT_INSPECCION,
    schema: tarifasVigentesVisitasResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) return [] as TarifaVigenteVisita[];
        return data.data.tarifas;
      },
    },
  });

  return query;
}
