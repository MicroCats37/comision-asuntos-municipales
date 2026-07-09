/**
 * Hooks para obtener tarifas vigentes de los endpoints GET /tarifas-vigentes.
 * Se usan para alimentar el selector de tarifas en los formularios.
 */
import type { z } from "zod";
import { useApiQuery } from "@/hooks";
import { tarifasVigentesHabilitacionUrbanaResponseSchema } from "../schemas/liquidacion-habilitacion-urbana.schema";
import type { TarifaVigenteHabilitacionUrbana } from "../types/liquidacion-habilitacion-urbana.types";
import { tarifasVigentesInspeccionObraResponseSchema } from "../schemas/liquidacion-inspeccion-obra.schema";
import type { TarifaVigenteInspeccionObra } from "../types/liquidacion-inspeccion-obra.types";
import { tarifasVigentesMecanicaSuelosResponseSchema } from "../schemas/liquidacion-mecanica-suelos.schema";
import type { TarifaVigenteMecanicaSuelos } from "../types/liquidacion-mecanica-suelos.types";
import { tarifasVigentesImpactoVialResponseSchema } from "../schemas/liquidacion-impacto-vial.schema";
import type { TarifaVigenteImpactoVial } from "../types/liquidacion-impacto-vial.types";
import { tarifasVigentesTaludesResponseSchema } from "../schemas/liquidacion-taludes.schema";
import type { TarifaVigenteTaludes } from "../types/liquidacion-taludes.types";

export interface TarifasVigentesInspeccionFilters {
  tramite_accion?: string;
  categoria?: string;
}

/**
 * Hook para obtener tarifas vigentes de Inspección de Obra.
 * Versión específica sin kind dispatch.
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
    z.infer<typeof tarifasVigentesInspeccionObraResponseSchema>,
    TarifaVigenteInspeccionObra[]
  >({
    queryKey: [
      "liquidaciones",
      "tarifas-vigentes",
      "inspeccion-obra",
      filters?.tramite_accion,
      filters?.categoria,
    ],
    url: "/liquidaciones/inspeccion-obra/tarifas-vigentes",
    schema: tarifasVigentesInspeccionObraResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) return [] as TarifaVigenteInspeccionObra[];
        return data.data.tarifas;
      },
    },
  });

  return query;
}

/**
 * Hook para obtener tarifas vigentes de Habilitación Urbana.
 * Versión específica sin kind dispatch.
 *
 * @param filters - Filtros opcionales (tramite_accion)
 */
export function useTarifasVigentesHabilitacionUrbana(
  filters?: { tramite_accion?: string },
) {
  const params: Record<string, string> = {};
  if (filters?.tramite_accion) {
    params.tramite_accion = filters.tramite_accion;
  }

  const query = useApiQuery<
    z.infer<typeof tarifasVigentesHabilitacionUrbanaResponseSchema>,
    TarifaVigenteHabilitacionUrbana[]
  >({
    queryKey: ["liquidaciones", "tarifas-vigentes", "habilitacion-urbana", filters?.tramite_accion],
    url: "/liquidaciones/habilitacion-urbana/tarifas-vigentes",
    schema: tarifasVigentesHabilitacionUrbanaResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) return [] as TarifaVigenteHabilitacionUrbana[];
        return data.data.tarifas;
      },
    },
  });

  return query;
}

/**
 * Hook para obtener tarifas vigentes de Mecánica de Suelos.
 * Versión específica sin kind dispatch.
 *
 * @param filters - Filtros opcionales (tramite_accion)
 */
export function useTarifasVigentesMecanicaSuelos(
  filters?: { tramite_accion?: string },
) {
  const params: Record<string, string> = {};
  if (filters?.tramite_accion) {
    params.tramite_accion = filters.tramite_accion;
  }

  const query = useApiQuery<
    z.infer<typeof tarifasVigentesMecanicaSuelosResponseSchema>,
    TarifaVigenteMecanicaSuelos[]
  >({
    queryKey: ["liquidaciones", "tarifas-vigentes", "mecanica-suelos", filters?.tramite_accion],
    url: "/liquidaciones/mecanica-suelos/tarifas-vigentes",
    schema: tarifasVigentesMecanicaSuelosResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) return [] as TarifaVigenteMecanicaSuelos[];
        return data.data.tarifas;
      },
    },
  });

  return query;
}

/**
 * Hook para obtener tarifas vigentes de Impacto Vial.
 * Versión específica sin kind dispatch.
 *
 * @param filters - Filtros opcionales (tramite_accion)
 */
export function useTarifasVigentesImpactoVial(
  filters?: { tramite_accion?: string },
) {
  const params: Record<string, string> = {};
  if (filters?.tramite_accion) {
    params.tramite_accion = filters.tramite_accion;
  }

  const query = useApiQuery<
    z.infer<typeof tarifasVigentesImpactoVialResponseSchema>,
    TarifaVigenteImpactoVial[]
  >({
    queryKey: ["liquidaciones", "tarifas-vigentes", "impacto-vial", filters?.tramite_accion],
    url: "/liquidaciones/impacto-vial/tarifas-vigentes",
    schema: tarifasVigentesImpactoVialResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) return [] as TarifaVigenteImpactoVial[];
        return data.data.tarifas;
      },
    },
  });

  return query;
}

/**
 * Hook para obtener tarifas vigentes de Taludes.
 * Versión específica sin kind dispatch.
 *
 * @param filters - Filtros opcionales (tramite_accion)
 */
export function useTarifasVigentesTaludes(
  filters?: { tramite_accion?: string },
) {
  const params: Record<string, string> = {};
  if (filters?.tramite_accion) {
    params.tramite_accion = filters.tramite_accion;
  }

  const query = useApiQuery<
    z.infer<typeof tarifasVigentesTaludesResponseSchema>,
    TarifaVigenteTaludes[]
  >({
    queryKey: ["liquidaciones", "tarifas-vigentes", "taludes", filters?.tramite_accion],
    url: "/liquidaciones/taludes/tarifas-vigentes",
    schema: tarifasVigentesTaludesResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) return [] as TarifaVigenteTaludes[];
        return data.data.tarifas;
      },
    },
  });

  return query;
}
