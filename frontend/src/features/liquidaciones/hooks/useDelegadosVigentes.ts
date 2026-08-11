/**
 * Hook para obtener delegados vigentes para una municipalidad, tipo de liquidacion y tarifa.
 * Usa useApiQuery genérico del proyecto.
 */

import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { DelegadoVigente } from "../types/liquidacion-edificaciones.types";

/** Data payload schema for delegado vigente */
const especialidadBasicaDelegadoSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const delegadoVigentePayloadSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
  especialidad: especialidadBasicaDelegadoSchema,
  tipo: z.string(),
});

/** Wrapper schema for delegados vigentes API response */
export const delegadosVigentesResponseSchema = apiResponseSchema(
  z.object({
    delegados: z.array(delegadoVigentePayloadSchema),
  }),
);

export function useDelegadosVigentes(
  municipalidadId: string | null,
  tipoLiquidacion: string | null,
  revisionId: string | null,
) {
  const query = useApiQuery<
    z.infer<typeof delegadosVigentesResponseSchema>,
    DelegadoVigente[]
  >({
    queryKey: [
      "liquidaciones",
      "delegados-vigentes",
      municipalidadId,
      tipoLiquidacion,
      revisionId,
    ],
    url: "/liquidaciones/delegados/vigentes",
    params:
      municipalidadId && tipoLiquidacion && revisionId
        ? {
            municipalidad_id: municipalidadId,
            tipo_liquidacion: tipoLiquidacion,
            revision_id: revisionId,
          }
        : undefined,
    schema: delegadosVigentesResponseSchema,
    queryOptions: {
      enabled: !!municipalidadId && !!tipoLiquidacion && !!revisionId,
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) {
          return [] as DelegadoVigente[];
        }
        return data.data.delegados;
      },
    },
  });

  return query;
}
