/**
 * Hooks para Nueva Revisión de Liquidación.
 */
import { useQueryClient } from "@tanstack/react-query";
import type { z } from "zod";
import { useApiCreate, useApiQuery } from "@/hooks";
import {
  liquidacionEdificacionOutResponseSchema,
  nuevaRevisionFormularioResponseSchema,
} from "../schemas/liquidacion.schema";
import type {
  LiquidacionEdificacionOut,
  NuevaRevisionFormData,
  NuevaRevisionFormularioResponse,
} from "../types/liquidacion-edificaciones";

const BASE_URL = "/liquidaciones/edificaciones";

/**
 * Hook para obtener formulario de nueva revisión.
 * Provee proyectistas_actuales disponibles para seleccionar.
 *
 * @param liquidacionPreviaId — UUID de la liquidación previa
 * @param enabled — si false, no se ejecuta la query (default: true)
 */
export function useNuevaRevisionFormulario(
  liquidacionPreviaId: string | null,
  enabled = true,
) {
  const query = useApiQuery<
    z.infer<typeof nuevaRevisionFormularioResponseSchema>,
    NuevaRevisionFormularioResponse | null
  >({
    queryKey: [
      "liquidaciones",
      "nueva-revision",
      "formulario",
      liquidacionPreviaId,
    ],
    url: `${BASE_URL}/nueva-revision/formulario`,
    params: { liquidacion_previa_id: liquidacionPreviaId ?? "" },
    schema: nuevaRevisionFormularioResponseSchema,
    queryOptions: {
      enabled: enabled && !!liquidacionPreviaId,
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => data.data ?? null,
    },
  });

  return query;
}

/**
 * Hook para crear nueva revisión de liquidación.
 * Retorna LiquidacionEdificacionOut plano (backend Phase 4+).
 */
export function useCrearNuevaRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof liquidacionEdificacionOutResponseSchema>,
    NuevaRevisionFormData
  >({
    url: `${BASE_URL}/nueva-revision`,
    schema: liquidacionEdificacionOutResponseSchema,
    options: {
      onSuccess: () => {
        // Invalidate liquidaciones list queries so cards refresh
        queryClient.invalidateQueries({
          queryKey: ["liquidaciones", "edificaciones"],
        });
        queryClient.invalidateQueries({
          queryKey: ["liquidaciones", "no-edificacion"],
        });
      },
    },
  });

  // Wrapper that sends payload directly and extracts flat LiquidacionEdificacionOut
  const crearMutation = {
    ...mutation,
    mutate: (payload: NuevaRevisionFormData) => {
      mutation.mutate(payload);
    },
    mutateAsync: async (
      payload: NuevaRevisionFormData,
    ): Promise<LiquidacionEdificacionOut> => {
      const result = await mutation.mutateAsync(payload);
      return (result as { data: LiquidacionEdificacionOut }).data;
    },
  };

  return crearMutation;
}
