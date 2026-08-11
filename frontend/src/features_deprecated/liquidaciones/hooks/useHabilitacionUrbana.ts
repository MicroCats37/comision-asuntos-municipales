/**
 * Hooks para crear y cotizar liquidaciones de Habilitación Urbana (primera revisión).
 * Endpoint: POST /liquidaciones/habilitacion-urbana/primera-revision
 * Endpoint: POST /liquidaciones/habilitacion-urbana/cotizar/primera-revision
 *
 * Versión específica para HU — sin dispatch por kind.
 */
import { useQueryClient } from "@tanstack/react-query";
import type { z } from "zod";
import { useApiCreate } from "@/hooks";
import {
  cotizacionHabilitacionUrbanaResponseSchema,
  crearHabilitacionUrbanaResponseSchema,
} from "../schemas/liquidacion-habilitacion-urbana.schema";
import type {
  CotizacionHabilitacionUrbanaResponse,
  CrearHabilitacionUrbanaPrimeraRevisionIn,
} from "../types/liquidacion-habilitacion-urbana.types";
import { habilitacionUrbanaService } from "../services/habilitacion-urbana.service";

/**
 * Hook para crear primera revisión de Habilitación Urbana.
 */
export function useCrearHabilitacionUrbanaPrimeraRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof crearHabilitacionUrbanaResponseSchema>,
    { liquidacion: CrearHabilitacionUrbanaPrimeraRevisionIn }
  >({
    url: "/liquidaciones/habilitacion-urbana/primera-revision",
    schema: crearHabilitacionUrbanaResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  const crearMutation = {
    ...mutation,
    mutate: (payload: CrearHabilitacionUrbanaPrimeraRevisionIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (payload: CrearHabilitacionUrbanaPrimeraRevisionIn) => {
      return mutation.mutateAsync({ liquidacion: payload });
    },
  };

  return crearMutation;
}

/**
 * Hook para cotizar primera revisión de Habilitación Urbana.
 */
export function useCotizarHabilitacionUrbanaPrimeraRevision() {
  const mutation = useApiCreate<
    z.infer<typeof cotizacionHabilitacionUrbanaResponseSchema>,
    { liquidacion: { area_solicitada: number; tarifas_ids: string[] } }
  >({
    url: "/liquidaciones/habilitacion-urbana/cotizar/primera-revision",
    schema: cotizacionHabilitacionUrbanaResponseSchema,
    options: {},
  });

  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: { area_solicitada: number; tarifas_ids: string[] }) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (
      payload: { area_solicitada: number; tarifas_ids: string[] },
    ): Promise<CotizacionHabilitacionUrbanaResponse> => {
      const result = await mutation.mutateAsync({ liquidacion: payload });
      return result.data as CotizacionHabilitacionUrbanaResponse;
    },
  };

  return cotizacionMutation;
}
