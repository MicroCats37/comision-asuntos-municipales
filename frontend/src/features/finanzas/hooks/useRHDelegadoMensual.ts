/**
 * Hooks para cotización y creación de RH Mensual de Delegado.
 * Endpoints:
 *   POST /finanzas/recibos-delegados/cotizar
 *   POST /finanzas/recibos-delegados/crear
 */
import { useQueryClient } from "@tanstack/react-query";
import { useApiCreate } from "@/hooks";
import type {
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
