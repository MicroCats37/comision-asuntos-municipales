/**
 * Hook para crear liquidaciones.
 * Usa useApiCreate genérico del proyecto.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import type { z } from "zod";
import { useApiCreate } from "@/hooks";
import { liquidacionEdificacionOutResponseSchema } from "../schemas/liquidacion.schema";
import type {
  LiquidacionEdificacionOut,
  PrimeraRevisionFormData,
} from "../types/liquidacion-edificaciones";

const BASE_URL = "/liquidaciones/edificaciones";

export function useCrearPrimeraRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof liquidacionEdificacionOutResponseSchema>,
    { liquidacion: PrimeraRevisionFormData }
  >({
    url: `${BASE_URL}/primera-revision`,
    schema: liquidacionEdificacionOutResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  // Wrapper that formats payload as { liquidacion: ... } for the API
  // and extracts the flat LiquidacionEdificacionOut from the response
  const crearMutation = useMemo(() => ({
    ...mutation,
    mutate: (payload: PrimeraRevisionFormData) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (
      payload: PrimeraRevisionFormData,
    ): Promise<LiquidacionEdificacionOut> => {
      const result = await mutation.mutateAsync({ liquidacion: payload });
      return (result as unknown as { data: LiquidacionEdificacionOut }).data;
    },
  }), [mutation]);

  return crearMutation;
}
