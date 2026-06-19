/**
 * Hook para crear liquidaciones.
 * Usa useApiCreate genérico del proyecto.
 */
import { useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { useApiCreate } from "@/hooks";
import { liquidacionSnapshotResponseSchema } from "../schemas/liquidacion.schema";
import type {
  LiquidacionSnapshot,
  PrimeraRevisionFormData,
} from "../types/liquidacion-edificaciones";

const BASE_URL = "/liquidaciones/edificaciones";

export function useCrearPrimeraRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof liquidacionSnapshotResponseSchema>,
    { liquidacion: PrimeraRevisionFormData }
  >({
    url: `${BASE_URL}/primera-revision`,
    schema: liquidacionSnapshotResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  // Wrapper that formats payload as { liquidacion: ... } for the API
  const crearMutation = {
    ...mutation,
    mutate: (payload: PrimeraRevisionFormData) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (payload: PrimeraRevisionFormData) => {
      return mutation.mutateAsync({ liquidacion: payload });
    },
  };

  return crearMutation;
}