/**
 * Hooks para cotización, creación y sincronización (PATCH) de RH Mensual de Delegado.
 * Endpoints:
 *   POST  /finanzas/recibos-delegados/cotizar
 *   POST  /finanzas/recibos-delegados/crear
 *   PATCH /finanzas/recibos-delegados/{rh_id}
 */
import { useQueryClient } from "@tanstack/react-query";
import { useApiCreate, useApiUpdate } from "@/hooks";
import type {
  RHDelegadoActualizarIn,
  RHDelegadoCotizar,
  RHDelegadoCotizarIn,
} from "../schemas/rh-delegado-mensual.schema";
import { RHDelegadoCotizarResponseSchema } from "../schemas/rh-delegado-mensual.schema";

const cotizarResponseSchema = RHDelegadoCotizarResponseSchema;
type CotizarResponseType = {
  success: boolean;
  data: RHDelegadoCotizar | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

const crearResponseSchema = RHDelegadoCotizarResponseSchema;
type CrearResponseType = CotizarResponseType;

export function useCotizarRHDelegado() {
  const mutation = useApiCreate<CotizarResponseType, RHDelegadoCotizarIn>({
    url: "/finanzas/recibos-delegados/cotizar",
    schema: cotizarResponseSchema,
    options: {
      onSuccess: () => {
        // Cotizar no invalida queries — solo prepara preview
      },
    },
  });

  return {
    ...mutation,
    cotizar: mutation.mutateAsync,
  };
}

export function useCrearRHDelegado() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<CrearResponseType, RHDelegadoCotizarIn>({
    url: "/finanzas/recibos-delegados/crear",
    schema: crearResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "recibos-delegados"],
        });
      },
    },
  });

  return {
    ...mutation,
    crear: mutation.mutateAsync,
  };
}

/**
 * Sincroniza el conjunto final de detalles de un RH mensual de delegado.
 *
 * El `items` del payload ES el conjunto final: las filas con `detalle_id` se
 * conservan, las que no lo tienen se agregan y las persistidas ausentes se
 * retiran. La metadata compartida de la asignación nunca se modifica.
 */
export function useActualizarRHDelegado(rhId: string) {
  const queryClient = useQueryClient();

  const mutation = useApiUpdate<CrearResponseType, RHDelegadoActualizarIn>({
    url: `/finanzas/recibos-delegados/${rhId}`,
    method: "PATCH",
    schema: crearResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "recibos-delegados"],
        });
      },
    },
  });

  return {
    ...mutation,
    actualizar: mutation.mutateAsync,
  };
}
