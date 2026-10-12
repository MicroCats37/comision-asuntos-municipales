/**
 * Hook para eliminar un Recibo de Honorario Mensual de Delegado.
 * Endpoint: DELETE /finanzas/recibos-delegados/{id}/eliminar
 */
import { useQueryClient } from "@tanstack/react-query";
import type { RHDelegadoDelete } from "@/features/finanzas/schemas/recibo-delete.schema";
import { useApiDelete } from "@/hooks";

type DeleteResponseType = {
  success: boolean;
  data: RHDelegadoDelete | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

export function useEliminarReciboDelegado() {
  const queryClient = useQueryClient();

  const mutation = useApiDelete<DeleteResponseType, string>({
    getUrl: (id) => `/finanzas/recibos-delegados/${id}/eliminar`,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "recibos-delegados"],
        });
      },
    },
  });

  return {
    ...mutation,
    eliminar: mutation.mutateAsync,
  };
}
