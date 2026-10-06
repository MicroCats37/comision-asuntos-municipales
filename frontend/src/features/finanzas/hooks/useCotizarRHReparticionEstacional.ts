/**
 * Hook para cotizar una Reparticion Estacional (preview, sin persistir).
 * Endpoint: POST /finanzas/reparticiones-estacionales/cotizar
 */
import { useApiCreate } from "@/hooks";
import type {
  RHReparticionEstacionalCotizar,
  RHReparticionEstacionalCotizarIn,
} from "../schemas/rh-reparticion-estacional.schema";
import { RHReparticionEstacionalCotizarResponseSchema } from "../schemas/rh-reparticion-estacional.schema";

type CotizarResponseType = {
  success: boolean;
  data: RHReparticionEstacionalCotizar | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

export function useCotizarRHReparticionEstacional() {
  const mutation = useApiCreate<
    CotizarResponseType,
    RHReparticionEstacionalCotizarIn
  >({
    url: "/finanzas/reparticiones-estacionales/cotizar",
    schema: RHReparticionEstacionalCotizarResponseSchema,
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
