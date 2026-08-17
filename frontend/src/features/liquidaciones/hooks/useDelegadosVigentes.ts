/**
 * Hook para obtener delegados vigentes para una municipalidad, tipo de liquidacion y tarifa.
 * Usa useApiQuery genérico del proyecto.
 *
 * `revisionId` es OPCIONAL: cuando se omite (null), el hook consulta con
 * municipalidad_id + tipo_liquidacion (caso GestionarDelegadosModal, que no
 * conoce la revisión). La queryKey conserva el slot para compartir cache
 * con los consumidores que sí pasan revisión.
 */

import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { DelegadoVigente } from "../schemas/delegado-vigente.schema";

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
  revisionId: string | null = null,
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
      municipalidadId && tipoLiquidacion
        ? {
            municipalidad_id: municipalidadId,
            tipo_liquidacion: tipoLiquidacion,
            ...(revisionId ? { revision_id: revisionId } : {}),
          }
        : undefined,
    schema: delegadosVigentesResponseSchema,
    queryOptions: {
      enabled: !!municipalidadId && !!tipoLiquidacion,
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
