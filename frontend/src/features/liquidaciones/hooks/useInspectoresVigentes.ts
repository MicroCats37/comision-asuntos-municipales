/**
 * Hook para obtener inspectores seleccionables/elegibles para una liquidación de Inspección de Obra.
 *
 * Endpoint: GET /liquidaciones/inspectores/seleccionables
 * Filtros: tipo_liquidacion (requerido, el de la previa), categoria (opcional), q (búsqueda nombre/CIP).
 * Sin paginación.
 *
 * La búsqueda es BAJO DEMANDA: solo consulta cuando `enabled` se vuelve true
 * (el botón "Buscar" del smart field lo activa cuando ya hay tipo_liquidacion).
 */

import type { z } from "zod";
import {
  InspectoresVigentesResponseSchema,
  type InspectorVigenteSchema,
} from "@/features/inspectores/schemas/inspector-vigente.schema";
import { useApiQuery } from "@/hooks";

/** Wrapper schema para inspectores seleccionables API response */
export const inspectoresVigentesResponseSchema =
  InspectoresVigentesResponseSchema;

/**
 * Hook para obtener inspectores seleccionables/elegibles.
 *
 * @param tipoLiquidacion - Tipo de liquidación de la previa (EDIFICACION o HABILITACION_URBANA)
 * @param categoria - Categoría opcional para filtrar
 * @param q - Búsqueda por nombre/CIP (opcional)
 * @param enabled - Controla si se consulta (el botón "Buscar" del form lo activa)
 */
export function useInspectoresVigentes(
  tipoLiquidacion?: string | null,
  categoria?: string | null,
  q?: string,
  enabled = false,
) {
  const query = useApiQuery<
    z.infer<typeof InspectoresVigentesResponseSchema>,
    z.infer<typeof InspectorVigenteSchema>[]
  >({
    queryKey: [
      "liquidaciones",
      "inspectores-seleccionables",
      tipoLiquidacion ?? "",
      categoria ?? "",
      q ?? "",
    ],
    url: "/liquidaciones/inspectores/seleccionables",
    params: {
      tipo_liquidacion: tipoLiquidacion ?? "",
      ...(categoria ? { categoria } : {}),
      ...(q ? { q } : {}),
    },
    schema: inspectoresVigentesResponseSchema,
    queryOptions: {
      enabled,
      staleTime: 0,
      select: (data) => {
        if (!data.data) {
          return [] as z.infer<typeof InspectorVigenteSchema>[];
        }
        return data.data.inspectores;
      },
    },
  });

  return query;
}
