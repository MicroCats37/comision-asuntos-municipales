/**
 * Hooks para crear y cotizar liquidaciones de Mecánica de Suelos (primera revisión).
 * Endpoint: POST /liquidaciones/mecanica-suelos/primera-revision
 * Endpoint: POST /liquidaciones/mecanica-suelos/cotizar/primera-revision
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
 * Hook para crear primera revisión de Mecánica de Suelos.
 */
export function useCrearMecanicaSuelosPrimeraRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof crearLiquidacionNoEdificacionResponseSchema>,
    { liquidacion: LiquidacionM2BaseIn }
  >({
    url: "/liquidaciones/mecanica-suelos/primera-revision",
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
 * Hook para cotizar primera revisión de Mecánica de Suelos.
 */
export function useCotizarMecanicaSuelosPrimeraRevision() {
  const mutation = useApiCreate<
    z.infer<typeof cotizacionNoEdificacionResponseSchema>,
    { liquidacion: { tipo_liquidacion: "mecanica-suelos"; area_solicitada: number; municipalidad_id: string; tarifas_ids: string[] } }
  >({
    url: "/liquidaciones/mecanica-suelos/cotizar/primera-revision",
    schema: cotizacionNoEdificacionResponseSchema,
    options: {},
  });

  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: { area_solicitada: number; municipalidad_id: string; tarifas_ids: string[] }) => {
      mutation.mutate({
        liquidacion: {
          tipo_liquidacion: "mecanica-suelos" as const,
          ...payload,
        },
      });
    },
    mutateAsync: async (
      payload: { area_solicitada: number; municipalidad_id: string; tarifas_ids: string[] },
    ): Promise<CotizacionNoEdificacionResponse> => {
      const result = await mutation.mutateAsync({
        liquidacion: {
          tipo_liquidacion: "mecanica-suelos" as const,
          ...payload,
        },
      });
      return result.data as CotizacionNoEdificacionResponse;
    },
  };

  return cotizacionMutation;
}
