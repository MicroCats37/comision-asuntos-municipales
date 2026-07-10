/**
 * Hooks para crear y cotizar liquidaciones de Taludes (primera revisión).
 * Endpoint: POST /liquidaciones/taludes/primera-revision
 * Endpoint: POST /liquidaciones/taludes/cotizar/primera-revision
 *
 * Versión específica para Taludes — sin dispatch por kind.
 */
import { useQueryClient } from "@tanstack/react-query";
import type { z } from "zod";
import { useApiCreate } from "@/hooks";
import {
  cotizacionTaludesResponseSchema,
  crearTaludesResponseSchema,
} from "../schemas/liquidacion-taludes.schema";
import type {
  CotizacionTaludesResponse,
  CrearTaludesPrimeraRevisionIn,
} from "../types/liquidacion-taludes.types";

/**
 * Hook para crear primera revisión de Taludes.
 */
export function useCrearTaludesPrimeraRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof crearTaludesResponseSchema>,
    { liquidacion: CrearTaludesPrimeraRevisionIn }
  >({
    url: "/liquidaciones/taludes/primera-revision",
    schema: crearTaludesResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  const crearMutation = {
    ...mutation,
    mutate: (payload: CrearTaludesPrimeraRevisionIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (payload: CrearTaludesPrimeraRevisionIn) => {
      return mutation.mutateAsync({ liquidacion: payload });
    },
  };

  return crearMutation;
}

/**
 * Hook para cotizar primera revisión de Taludes.
 */
export function useCotizarTaludesPrimeraRevision() {
  const mutation = useApiCreate<
    z.infer<typeof cotizacionTaludesResponseSchema>,
    { liquidacion: { area_solicitada: number; tarifas_ids: string[] } }
  >({
    url: "/liquidaciones/taludes/cotizar/primera-revision",
    schema: cotizacionTaludesResponseSchema,
    options: {},
  });

  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: { area_solicitada: number; tarifas_ids: string[] }) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (
      payload: { area_solicitada: number; tarifas_ids: string[] },
    ): Promise<CotizacionTaludesResponse> => {
      const result = await mutation.mutateAsync({ liquidacion: payload });
      return result.data as CotizacionTaludesResponse;
    },
  };

  return cotizacionMutation;
}
