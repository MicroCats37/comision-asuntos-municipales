/**
 * Hooks para crear y cotizar liquidaciones de Inspección de Obra (primera revisión).
 * Endpoint: POST /liquidaciones/inspeccion-obra/primera-revision
 * Endpoint: POST /liquidaciones/inspeccion-obra/cotizar/primera-revision
 *
 * Versión específica para Inspección de Obra — sin dispatch por kind.
 */
import { useQueryClient } from "@tanstack/react-query";
import type { z } from "zod";
import { useApiCreate } from "@/hooks";
import {
  cotizacionIOResponseSchema,
  crearInspeccionObraResponseSchema,
} from "../schemas/liquidacion-inspeccion-obra.schema";
import type {
  CotizacionIOResponse,
  CrearInspeccionObraPrimeraRevisionIn,
} from "../types/liquidacion-inspeccion-obra.types";
import type { CotizarInspeccionObraPrimeraRevisionIn } from "../types/liquidacion-inspeccion-obra.types";

/**
 * Hook para crear primera revisión de Inspección de Obra.
 */
export function useCrearInspeccionObraPrimeraRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof crearInspeccionObraResponseSchema>,
    { liquidacion: CrearInspeccionObraPrimeraRevisionIn }
  >({
    url: "/liquidaciones/inspeccion-obra/primera-revision",
    schema: crearInspeccionObraResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  const crearMutation = {
    ...mutation,
    mutate: (payload: CrearInspeccionObraPrimeraRevisionIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (payload: CrearInspeccionObraPrimeraRevisionIn) => {
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
    z.infer<typeof cotizacionIOResponseSchema>,
    { liquidacion: CotizarInspeccionObraPrimeraRevisionIn }
  >({
    url: "/liquidaciones/inspeccion-obra/cotizar/primera-revision",
    schema: cotizacionIOResponseSchema,
    options: {},
  });

  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: CotizarInspeccionObraPrimeraRevisionIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (
      payload: CotizarInspeccionObraPrimeraRevisionIn,
    ): Promise<CotizacionIOResponse> => {
      const result = await mutation.mutateAsync({ liquidacion: payload });
      return result.data as CotizacionIOResponse;
    },
  };

  return cotizacionMutation;
}
