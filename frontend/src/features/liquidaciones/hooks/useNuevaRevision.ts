/**
 * Hooks para Nueva Revisión de Liquidación.
 */
import { useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { useApiCreate, useApiQuery } from "@/hooks";
import {
  nuevaRevisionFormularioResponseSchema,
  liquidacionSnapshotResponseSchema,
} from "../schemas/liquidacion.schema";
import type {
  NuevaRevisionFormularioResponse,
  NuevaRevisionFormData,
  LiquidacionSnapshot,
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
    queryKey: ["liquidaciones", "nueva-revision", "formulario", liquidacionPreviaId],
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
 */
export function useCrearNuevaRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof liquidacionSnapshotResponseSchema>,
    NuevaRevisionFormData
  >({
    url: `${BASE_URL}/nueva-revision`,
    schema: liquidacionSnapshotResponseSchema,
    options: {
      onSuccess: () => {
        // Invalidate snapshot list queries so cards refresh
        queryClient.invalidateQueries({ queryKey: ["liquidaciones", "snapshots"] });
        // Invalidate liquidaciones list query if still used
        queryClient.invalidateQueries({ queryKey: ["liquidaciones", "list"] });
      },
    },
  });

  // Wrapper that sends payload directly and extracts inner data
  const crearMutation = {
    ...mutation,
    mutate: (payload: NuevaRevisionFormData) => {
      mutation.mutate(payload);
    },
    mutateAsync: async (payload: NuevaRevisionFormData): Promise<LiquidacionSnapshot> => {
      const result = await mutation.mutateAsync(payload);
      return (result as { data: LiquidacionSnapshot }).data;
    },
  };

  return crearMutation;
}
