/**
 * Hook para obtener inspectores vigentes/elegibles para una liquidación de Inspección de Obra.
 *
 * Tres modos de uso:
 * - Por liquidacion existente: GET /{liquidacion_id}/inspectores/vigentes
 *   (excluye inspectores ya asociados a esa liquidacion)
 * - Por liquidacion previa: GET /inspectores/vigentes?liquidacion_previa_id=
 *   (deriva el tipo de la liquidacion previa, para formularios de creación)
 * - Por tipo de liquidacion: GET /inspectores/vigentes?tipo_liquidacion=
 *   (para formularios de creación, sin exclusion)
 */

import type { z } from "zod";
import {
  InspectoresVigentesResponseSchema,
  type InspectorVigenteSchema,
} from "@/features/inspectores/schemas/inspector-vigente.schema";
import { useApiQuery } from "@/hooks";

/** Wrapper schema para inspectores vigentes API response */
export const inspectoresVigentesResponseSchema =
  InspectoresVigentesResponseSchema;

/**
 * Hook para obtener inspectores vigentes/elegibles.
 *
 * @param liquidacionId - ID de liquidación existente (para post-create, excluye ya asociados)
 * @param tipoLiquidacion - Tipo de liquidación (EDIFICACION o HABILITACION_URBANA)
 * @param liquidacionPreviaId - ID de la liquidación previa (para pre-create, deriva el tipo automáticamente)
 */
export function useInspectoresVigentes(
  liquidacionId: string | null,
  tipoLiquidacion?: string,
  liquidacionPreviaId?: string | null,
) {
  // liquidacionPreviaId takes precedence for creation forms
  const query = useApiQuery<
    z.infer<typeof InspectoresVigentesResponseSchema>,
    z.infer<typeof InspectorVigenteSchema>[]
  >({
    queryKey: [
      "liquidaciones",
      "inspectores-vigentes",
      liquidacionId ?? tipoLiquidacion ?? liquidacionPreviaId,
    ],
    url: liquidacionId
      ? `/liquidaciones/${liquidacionId}/inspectores/vigentes`
      : `/liquidaciones/inspectores/vigentes`,
    params: liquidacionId
      ? undefined
      : liquidacionPreviaId
        ? { liquidacion_previa_id: liquidacionPreviaId }
        : tipoLiquidacion
          ? { tipo_liquidacion: tipoLiquidacion }
          : undefined,
    schema: inspectoresVigentesResponseSchema,
    queryOptions: {
      enabled: !!(liquidacionId ?? tipoLiquidacion ?? liquidacionPreviaId),
      staleTime: 1000 * 60 * 5, // 5 minutes
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
