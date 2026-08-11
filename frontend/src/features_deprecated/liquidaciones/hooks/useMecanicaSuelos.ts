/**
 * Hooks para crear y cotizar liquidaciones de Mecánica de Suelos (primera revisión).
 * Endpoint: POST /liquidaciones/mecanica-suelos/primera-revision
 * Endpoint: POST /liquidaciones/mecanica-suelos/cotizar/primera-revision
 *
 * Versión específica para MS — sin dispatch por kind.
 */
import { useQueryClient } from "@tanstack/react-query";
import type { z } from "zod";
import { useApiCreate } from "@/hooks";
import {
  cotizacionMecanicaSuelosResponseSchema,
  crearMecanicaSuelosResponseSchema,
} from "../schemas/liquidacion-mecanica-suelos.schema";
import type {
  CotizacionMecanicaSuelosResponse,
  CrearMecanicaSuelosPrimeraRevisionIn,
} from "../types/liquidacion-mecanica-suelos.types";
import { mecanicaSuelosService } from "../services/mecanica-suelos.service";

/**
 * Hook para crear primera revisión de Mecánica de Suelos.
 */
export function useCrearMecanicaSuelosPrimeraRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof crearMecanicaSuelosResponseSchema>,
    { liquidacion: CrearMecanicaSuelosPrimeraRevisionIn }
  >({
    url: "/liquidaciones/mecanica-suelos/primera-revision",
    schema: crearMecanicaSuelosResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  const crearMutation = {
    ...mutation,
    mutate: (payload: CrearMecanicaSuelosPrimeraRevisionIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (payload: CrearMecanicaSuelosPrimeraRevisionIn) => {
      return mutation.mutateAsync({ liquidacion: payload });
    },
  };

  return crearMutation;
}

/**
 * Hook para cotizar primera revisión de Mecánica de Suelos.
 */
export function useCotizarMecanicaSuelosPrimeraRevision() {
  const mutation = useApiCreate<
    z.infer<typeof cotizacionMecanicaSuelosResponseSchema>,
    { liquidacion: { area_solicitada: number; tarifas_ids: string[] } }
  >({
    url: "/liquidaciones/mecanica-suelos/cotizar/primera-revision",
    schema: cotizacionMecanicaSuelosResponseSchema,
    options: {},
  });

  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: { area_solicitada: number; tarifas_ids: string[] }) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (
      payload: { area_solicitada: number; tarifas_ids: string[] },
    ): Promise<CotizacionMecanicaSuelosResponse> => {
      const result = await mutation.mutateAsync({ liquidacion: payload });
      return result.data as CotizacionMecanicaSuelosResponse;
    },
  };

  return cotizacionMutation;
}
