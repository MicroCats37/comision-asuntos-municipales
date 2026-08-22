/**
 * Hooks para cotización y creación de RH Mensual de Inspector.
 * Endpoints:
 *   POST /finanzas/recibos-inspectores/cotizar
 *   POST /finanzas/recibos-inspectores/crear
 */
import { useQueryClient } from "@tanstack/react-query";
import { useApiCreate } from "@/hooks";
import type {
  RHInspectorCotizar,
  RHInspectorCotizarIn,
} from "../schemas/rh-inspector-mensual.schema";
import { RHInspectorCotizarResponseSchema } from "../schemas/rh-inspector-mensual.schema";

const cotizarResponseSchema = RHInspectorCotizarResponseSchema;
type CotizarResponseType = {
  success: boolean;
  data: RHInspectorCotizar | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

const crearResponseSchema = RHInspectorCotizarResponseSchema;
type CrearResponseType = CotizarResponseType;

export function useCotizarRHInspector() {
  const mutation = useApiCreate<CotizarResponseType, RHInspectorCotizarIn>({
    url: "/finanzas/recibos-inspectores/cotizar",
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

export function useCrearRHInspector() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<CrearResponseType, RHInspectorCotizarIn>({
    url: "/finanzas/recibos-inspectores/crear",
    schema: crearResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "recibos-inspectores"],
        });
      },
    },
  });

  return {
    ...mutation,
    crear: mutation.mutateAsync,
  };
}
