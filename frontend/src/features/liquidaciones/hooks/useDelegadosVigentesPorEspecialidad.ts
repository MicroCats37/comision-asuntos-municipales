/**
 * Hook para obtener delegados vigentes filtrados por Especialidad de Revision.
 * Endpoint: GET /liquidaciones/delegados/vigentes-por-especialidad
 *
 * Parametros:
 *   especialidad_revision_id — UUID de EspecialidadRevision (REQUERIDO)
 *   fecha — YYYY-MM-DD opcional; por defecto hoy
 *
 * El parametro enabled permite controlar la query manualmente
 * (e.g. cuando especialidad_revision_id aun no se ha seleccionado).
 */
import type { z } from "zod";
import { useApiQuery } from "@/hooks";
import {
  DelegadosVigentesPorEspecialidadResponseSchema,
  type DelegadoVigentePorEspecialidad,
} from "../schemas/delegado-vigente-por-especialidad.schema";

/**
 * Normalize a date string or Date to YYYY-MM-DD in local time.
 * Handles ISO strings with time components by extracting the date part.
 * Returns null if input is null/undefined.
 */
function normalizeFecha(
  fecha: string | Date | null | undefined,
): string | null {
  if (!fecha) return null;
  const d = typeof fecha === "string" ? new Date(fecha) : fecha;
  if (isNaN(d.getTime())) return null;
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function useDelegadosVigentesPorEspecialidad(
  especialidadRevisionId: string | null,
  fecha: string | Date | null = null,
  enabled = true,
) {
  const normalizedFecha = normalizeFecha(fecha);

  const query = useApiQuery<
    z.infer<typeof DelegadosVigentesPorEspecialidadResponseSchema>,
    DelegadoVigentePorEspecialidad[]
  >({
    queryKey: [
      "liquidaciones",
      "delegados-vigentes-por-especialidad",
      especialidadRevisionId ?? "",
      normalizedFecha ?? "",
    ],
    url: "/liquidaciones/delegados/vigentes-por-especialidad",
    schema: DelegadosVigentesPorEspecialidadResponseSchema,
    params: especialidadRevisionId
      ? {
          especialidad_revision_id: especialidadRevisionId,
          ...(normalizedFecha ? { fecha: normalizedFecha } : {}),
        }
      : undefined,
    queryOptions: {
      enabled: !!especialidadRevisionId && enabled,
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) {
          return [] as DelegadoVigentePorEspecialidad[];
        }
        return data.data.delegados;
      },
    },
  });

  return query;
}
