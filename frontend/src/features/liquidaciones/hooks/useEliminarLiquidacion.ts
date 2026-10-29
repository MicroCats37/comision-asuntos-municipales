/**
 * Hook para eliminar (soft-delete) una liquidacion general.
 *
 * Endpoint: PATCH /liquidaciones/generales/{id}/eliminar
 * Payload:   { motivo: string }
 *
 * Usa useApiUpdate en modo directo (PATCH) con payload builder.
 * NO usa invalidateQueries — actualiza el cache manualmente con useLiquidacionesCacheUtils.
 * Remueve el item de todas las listas visibles y marca el detalle como eliminado.
 */

import { z } from "zod";
import { useApiUpdate } from "@/hooks/callsApi/useApiUpdate";
import { useLiquidacionesCacheUtils } from "./cache";

const EliminarLiquidacionSchema = z.object({
  motivo: z
    .string()
    .trim()
    .min(1, "El motivo de eliminación es obligatorio")
    .max(500, "El motivo no puede superar los 500 caracteres"),
});
export type EliminarLiquidacionPayload = z.infer<
  typeof EliminarLiquidacionSchema
>;

export function useEliminarLiquidacion(id: string) {
  const cacheUtils = useLiquidacionesCacheUtils();

  const mutation = useApiUpdate<unknown, EliminarLiquidacionPayload>({
    url: `/liquidaciones/generales/${id}/eliminar`,
    method: "PATCH",
    schema: EliminarLiquidacionSchema,
    options: {
      onSuccess: () => {
        // Remover de todas las listas visibles (tipo-específicas y generales)
        cacheUtils.removeVisibleItem(id);
        // Marcar el detalle general como eliminado
        cacheUtils.markDetailDeleted(id);
      },
    },
  });

  return mutation;
}
