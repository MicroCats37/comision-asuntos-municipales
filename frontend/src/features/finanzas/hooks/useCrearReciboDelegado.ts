/**
 * Hook para crear un Recibo de Honorario.
 * Endpoint: POST /finanzas/recibos-delegados
 * Body: { liquidacion_delegado_id: string }
 */
import { useQueryClient } from "@tanstack/react-query";
import { useApiCreate } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import {
  type ReciboHonorarioDelegado,
  reciboHonorarioDelegadoSchema,
} from "../schemas/recibo-honorario.schema";

const responseSchema = apiResponseSchema(reciboHonorarioDelegadoSchema);
type ResponseType = {
  success: boolean;
  data: ReciboHonorarioDelegado | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

export function useCrearReciboDelegado() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    ResponseType,
    { liquidacion_delegado_id: string }
  >({
    url: "/finanzas/recibos-delegados",
    schema: responseSchema,
    options: {
      onSuccess: () => {
        // Invalidate the list to refetch
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "recibos-delegados"],
        });
      },
    },
  });

  return mutation;
}
