/**
 * Hook para obtener revisiones vigentes de Impacto Vial.
 * Backend: GET /liquidaciones/impacto-vial/revisiones-vigentes
 * Respuesta: { data: { revisiones: RevisionVigente[] } }
 * Contrato idéntico a Edificaciones (mismas campos including especialidades M2M).
 */

import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { RevisionVigente } from "../types/revisiones-vigentes";

const revisionVigentePayloadSchema = z.object({
  id: z.string(),
  especialidades: z.array(
    z.object({
      id: z.string(),
      nombre: z.string(),
    }),
  ),
  tarifa_id: z.string(),
  porcentaje_liquidacion: z.number(),
  derecho_minimo: z.number(),
  derecho_maximo: z.number().nullable(),
  porcentaje_minimo_uit: z.number(),
  habilitada: z.boolean(),
});

const revisionesVigentesResponseSchema = apiResponseSchema(
  z.object({
    revisiones: z.array(revisionVigentePayloadSchema),
  }),
);

export interface RevisionesVigentesIVFilters {
  tipo_tramite?: string;
  tramite_accion?: string;
}

export function useRevisionesVigentesIV(filters?: RevisionesVigentesIVFilters) {
  const params: Record<string, string> = {};
  if (filters?.tipo_tramite) params.tipo_tramite = filters.tipo_tramite;
  if (filters?.tramite_accion) params.tramite_accion = filters.tramite_accion;

  const query = useApiQuery<
    z.infer<typeof revisionesVigentesResponseSchema>,
    RevisionVigente[]
  >({
    queryKey: ["liquidaciones", "revisiones-vigentes", "impacto-vial", filters?.tipo_tramite, filters?.tramite_accion],
    url: "/liquidaciones/impacto-vial/revisiones-vigentes",
    schema: revisionesVigentesResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 5,
      select: (data) => {
        if (!data.data) return [] as RevisionVigente[];
        return data.data.revisiones;
      },
    },
  });

  return query;
}
