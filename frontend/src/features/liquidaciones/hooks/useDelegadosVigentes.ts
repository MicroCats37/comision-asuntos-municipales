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

/**
 * Normalize a date string or Date to YYYY-MM-DD in local time.
 * Handles ISO strings with time components by extracting the date part.
 * Returns null if input is null/undefined.
 */
function normalizeFecha(fecha: string | Date | null | undefined): string | null {
  if (!fecha) return null;
  const d = typeof fecha === "string" ? new Date(fecha) : fecha;
  if (isNaN(d.getTime())) return null;
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function useDelegadosVigentes(
  municipalidadId: string | null,
  tipoLiquidacion: string | null,
  revisionId: string | null = null,
  fechaRegistro: string | Date | null = null,
) {
  const normalizedFecha = normalizeFecha(fechaRegistro);

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
      normalizedFecha,
    ],
    url: "/liquidaciones/delegados/vigentes",
    params:
      municipalidadId && tipoLiquidacion
        ? {
            municipalidad_id: municipalidadId,
            tipo_liquidacion: tipoLiquidacion,
            ...(revisionId ? { revision_id: revisionId } : {}),
            ...(normalizedFecha ? { fecha: normalizedFecha } : {}),
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
