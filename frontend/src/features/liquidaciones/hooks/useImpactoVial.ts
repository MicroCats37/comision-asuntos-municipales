/**
 * Hooks para crear y cotizar liquidaciones de Impacto Vial (primera revisión).
 * Endpoint: POST /liquidaciones/impacto-vial/primera-revision
 * Endpoint: POST /liquidaciones/impacto-vial/cotizar/primera-revision
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
  LiquidacionM2BaseIn,
} from "../types/liquidacion-no-edificacion.types";

/**
 * Hook para crear primera revisión de Impacto Vial.
 */
export function useCrearImpactoVialPrimeraRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof crearLiquidacionNoEdificacionResponseSchema>,
    { liquidacion: LiquidacionM2BaseIn }
  >({
    url: "/liquidaciones/impacto-vial/primera-revision",
    schema: crearLiquidacionNoEdificacionResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones"] });
      },
    },
  });

  const crearMutation = {
    ...mutation,
    mutate: (payload: LiquidacionM2BaseIn) => {
      mutation.mutate({ liquidacion: payload });
    },
    mutateAsync: async (payload: LiquidacionM2BaseIn) => {
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
    z.infer<typeof cotizacionNoEdificacionResponseSchema>,
    { liquidacion: { tipo_liquidacion: "impacto-vial"; area_solicitada: number; municipalidad_id: string; tarifas_ids: string[] } }
  >({
    url: "/liquidaciones/impacto-vial/cotizar/primera-revision",
    schema: cotizacionNoEdificacionResponseSchema,
    options: {},
  });

  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: { area_solicitada: number; municipalidad_id: string; tarifas_ids: string[] }) => {
      mutation.mutate({
        liquidacion: {
          tipo_liquidacion: "impacto-vial" as const,
          ...payload,
        },
      });
    },
    mutateAsync: async (
      payload: { area_solicitada: number; municipalidad_id: string; tarifas_ids: string[] },
    ): Promise<CotizacionNoEdificacionResponse> => {
      const result = await mutation.mutateAsync({
        liquidacion: {
          tipo_liquidacion: "impacto-vial" as const,
          ...payload,
        },
      });
      return result.data as CotizacionNoEdificacionResponse;
    },
  };

  return cotizacionMutation;
}
