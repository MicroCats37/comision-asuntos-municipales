/**
 * Hook para editar (PATCH) una Reparticion Estacional (RH Trimestral).
 * Endpoint: PATCH /finanzas/reparticiones-estacionales/{id}
 *
 * El backend devuelve el mismo item compuesto del listado
 * (identidad + general + distribucion) y un mensaje humano en el primer
 * nivel del envelope — el toast lo produce la capa de mutación.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useApiUpdate } from "@/hooks";
import type {
  RHReparticionEstacional,
  RHReparticionEstacionalActualizarIn,
} from "../schemas/rh-reparticion-estacional.schema";
import { RHReparticionEstacionalResponseSchema } from "../schemas/rh-reparticion-estacional.schema";

type ActualizarResponseType = {
  success: boolean;
  data: RHReparticionEstacional | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

export function useActualizarRHReparticionEstacional(reparticionId: string) {
  const queryClient = useQueryClient();

  const mutation = useApiUpdate<
    ActualizarResponseType,
    RHReparticionEstacionalActualizarIn
  >({
    url: `/finanzas/reparticiones-estacionales/${reparticionId}`,
    method: "PATCH",
    schema: RHReparticionEstacionalResponseSchema,
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
    actualizar: mutation.mutateAsync,
  };
}
