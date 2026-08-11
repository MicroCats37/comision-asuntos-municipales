/**
 * Hooks para crear y cotizar liquidaciones de Impacto Vial (primera revisión).
 * Endpoint: POST /liquidaciones/impacto-vial/primera-revision
 * Endpoint: POST /liquidaciones/impacto-vial/cotizar/primera-revision
 *
 * Versión específica para IV — sin dispatch por kind.
 */
import { useQueryClient } from "@tanstack/react-query";
import type { z } from "zod";
import { useApiCreate } from "@/hooks";
import {
  cotizacionImpactoVialResponseSchema,
  crearImpactoVialResponseSchema,
} from "../schemas/liquidacion-impacto-vial.schema";
import type {
  CotizacionImpactoVialResponse,
  CrearImpactoVialPrimeraRevisionIn,
} from "../types/liquidacion-impacto-vial.types";

/**
 * Hook para crear primera revisión de Impacto Vial.
 */
export function useCrearImpactoVialPrimeraRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof crearImpactoVialResponseSchema>,
    { liquidacion: CrearImpactoVialPrimeraRevisionIn }
  >({
    url: "/liquidaciones/impacto-vial/primera-revision",
    schema: crearImpactoVialResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  const crearMutation = {
    ...mutation,
    mutate: (payload: CrearImpactoVialPrimeraRevisionIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (payload: CrearImpactoVialPrimeraRevisionIn) => {
      return mutation.mutateAsync({ liquidacion: payload });
    },
  };

  return crearMutation;
}

/**
 * Hook para cotizar primera revisión de Impacto Vial.
 */
export function useCotizarImpactoVialPrimeraRevision() {
  const mutation = useApiCreate<
    z.infer<typeof cotizacionImpactoVialResponseSchema>,
    { liquidacion: { valor_proyecto: number; tarifas_ids: string[] } }
  >({
    url: "/liquidaciones/impacto-vial/cotizar/primera-revision",
    schema: cotizacionImpactoVialResponseSchema,
    options: {},
  });

  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: { valor_proyecto: number; tarifas_ids: string[] }) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (
      payload: { valor_proyecto: number; tarifas_ids: string[] },
    ): Promise<CotizacionImpactoVialResponse> => {
      const result = await mutation.mutateAsync({ liquidacion: payload });
      return result.data as CotizacionImpactoVialResponse;
    },
  };

  return cotizacionMutation;
}
