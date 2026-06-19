/**
 * Hook para cotizar liquidaciones (sin guardar en BD).
 * Usa useApiCreate genérico del proyecto.
 */
import { useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { useApiCreate } from "@/hooks";
import {
  cotizacionQuoteResponseSchema,
  cotizacionPrimeraRevisionRequestSchema,
  cotizacionNuevaRevisionRequestSchema,
} from "../schemas/liquidacion.schema";
import type { CotizacionQuote } from "../types/liquidacion-edificaciones";

const BASE_URL = "/liquidaciones/edificaciones";

/**
 * Hook para cotizar primera revisión.
 * No guarda en BD, solo calcula los totales.
 */
export function useCotizacionPrimeraRevision() {
  const mutation = useApiCreate<
    z.infer<typeof cotizacionQuoteResponseSchema>,
    { proyecto_public_id: string; valor_proyecto: number }
  >({
    url: `${BASE_URL}/cotizar/primera-revision`,
    schema: cotizacionQuoteResponseSchema,
    options: {
      // No invalidamos queries porque no hay datos nuevos que refreshing
    },
  });

  // Wrapper que formatea el payload como { liquidacion: ... }
  const cotizacionMutation = {
    ...mutation,
    mutate: (payload: { proyecto_public_id: string; valor_proyecto: number }) => {
      mutation.mutate({ liquidacion: payload } as any);
    },
    mutateAsync: async (payload: { proyecto_public_id: string; valor_proyecto: number }) => {
      return mutation.mutateAsync({ liquidacion: payload } as any);
    },
  };

  return cotizacionMutation;
}

/**
 * Hook para cotizar nueva revisión.
 * No guarda en BD, solo calcula los totales.
 */
export function useCotizacionNuevaRevision() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    z.infer<typeof cotizacionQuoteResponseSchema>,
    { liquidacion_previa_id: string; revisiones_ids: string[] }
  >({
    url: `${BASE_URL}/cotizar/nueva-revision`,
    schema: cotizacionQuoteResponseSchema,
    options: {
      // No invalidamos queries porque no hay datos nuevos que refreshing
    },
  });

  return mutation;
}
