/**
 * Hooks para crear y cotizar liquidaciones de Inspección de Obra (primera revisión).
 * Endpoint: POST /liquidaciones/inspeccion-obra/primera-revision
 * Endpoint: POST /liquidaciones/inspeccion-obra/cotizar/primera-revision
 */
import { useQueryClient } from "@tanstack/react-query";
import type { z } from "zod";
import { useApiCreate } from "@/hooks";
import {
  cotizacionNoEdificacionResponseSchema,
  crearLiquidacionNoEdificacionResponseSchema,
} from "../schemas/liquidacion-no-edificacion.schema";
import type {
  CotizacionNoEdificacionResponse,
  CrearLiquidacionInspeccionObraIn,
  CotizarInspeccionObraPrimeraRevisionIn,
} from "../types/liquidacion-no-edificacion.types";

/**
 * Hook para crear primera revisión de Inspección de Obra.
 */
export function useCrearInspeccionObraPrimeraRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof crearLiquidacionNoEdificacionResponseSchema>,
    { liquidacion: CrearLiquidacionInspeccionObraIn }
  >({
    url: "/liquidaciones/inspeccion-obra/primera-revision",
    schema: crearLiquidacionNoEdificacionResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  const crearMutation = {
    ...mutation,
    mutate: (payload: CrearLiquidacionInspeccionObraIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (payload: CrearLiquidacionInspeccionObraIn) => {
      return mutation.mutateAsync({ liquidacion: payload });
    },
  };

  return crearMutation;
}

/**
 * Hook para cotizar primera revisión de Inspección de Obra.
 */
export function useCotizarInspeccionObraPrimeraRevision() {
  const mutation = useApiCreate<
    z.infer<typeof cotizacionNoEdificacionResponseSchema>,
    { liquidacion: CotizarInspeccionObraPrimeraRevisionIn }
  >({
    url: "/liquidaciones/inspeccion-obra/cotizar/primera-revision",
    schema: cotizacionNoEdificacionResponseSchema,
    options: {},
  });

  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: CotizarInspeccionObraPrimeraRevisionIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (
      payload: CotizarInspeccionObraPrimeraRevisionIn,
    ): Promise<CotizacionNoEdificacionResponse> => {
      const result = await mutation.mutateAsync({ liquidacion: payload });
      return result.data as CotizacionNoEdificacionResponse;
    },
  };

  return cotizacionMutation;
}
