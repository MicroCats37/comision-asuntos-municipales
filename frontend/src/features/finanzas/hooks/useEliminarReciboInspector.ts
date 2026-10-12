/**
 * Hook para eliminar un Recibo de Honorario Mensual de Inspector.
 * Endpoint: DELETE /finanzas/recibos-inspectores/{id}/eliminar
 */
import { useQueryClient } from "@tanstack/react-query";
import type { RHInspectorDelete } from "@/features/finanzas/schemas/recibo-delete.schema";
import { useApiDelete } from "@/hooks";

type DeleteResponseType = {
  success: boolean;
  data: RHInspectorDelete | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

export function useEliminarReciboInspector() {
  const queryClient = useQueryClient();

  const mutation = useApiDelete<DeleteResponseType, string>({
    getUrl: (id) => `/finanzas/recibos-inspectores/${id}/eliminar`,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "recibos-inspectores"],
        });
      },
    },
  });

  return {
    ...mutation,
    eliminar: mutation.mutateAsync,
  };
}
