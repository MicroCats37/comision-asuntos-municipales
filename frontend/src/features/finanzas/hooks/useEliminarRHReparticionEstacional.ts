/**
 * Hook para eliminar (soft-delete) una Reparticion Estacional.
 * Endpoint: DELETE /finanzas/reparticiones-estacionales/{id}
 *
 * El mensaje humano llega en el primer nivel del envelope: lo publica la
 * capa de mutación (useApiDelete), sin toasts duplicados en el componente.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useApiDelete } from "@/hooks";
import type { RHReparticionEstacionalDelete } from "../schemas/rh-reparticion-estacional.schema";

type DeleteResponseType = {
  success: boolean;
  data: RHReparticionEstacionalDelete | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

export function useEliminarRHReparticionEstacional() {
  const queryClient = useQueryClient();

  const mutation = useApiDelete<DeleteResponseType, string>({
    baseUrl: "/finanzas/reparticiones-estacionales",
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "reparticiones-estacionales"],
        });
      },
    },
  });

  return {
    ...mutation,
    eliminar: mutation.mutateAsync,
  };
}
