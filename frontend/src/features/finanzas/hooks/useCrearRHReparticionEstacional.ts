/**
 * Hook para crear una Reparticion Estacional (cotiza y persiste).
 * Endpoint: POST /finanzas/reparticiones-estacionales
 */
import { useQueryClient } from "@tanstack/react-query";
import { useApiCreate } from "@/hooks";
import type {
  RHReparticionEstacionalCotizar,
  RHReparticionEstacionalCotizarIn,
} from "../schemas/rh-reparticion-estacional.schema";
import { RHReparticionEstacionalCotizarResponseSchema } from "../schemas/rh-reparticion-estacional.schema";

type CrearResponseType = {
  success: boolean;
  data: RHReparticionEstacionalCotizar | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

export function useCrearRHReparticionEstacional() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    CrearResponseType,
    RHReparticionEstacionalCotizarIn
  >({
    url: "/finanzas/reparticiones-estacionales",
    schema: RHReparticionEstacionalCotizarResponseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "reparticiones-estacionales"],
        });
      },
    },
  });

  return {
    ...mutation,
    crear: mutation.mutateAsync,
  };
}
