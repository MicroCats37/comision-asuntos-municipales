/**
 * Hook para crear un Recibo de Honorario de Inspector.
 * Endpoint: POST /finanzas/recibos-inspectores
 * Body: { liquidacion_inspector_id: string, inspecciones_mes: number }
 */
import { useQueryClient } from "@tanstack/react-query";
import { useApiCreate } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import {
  type ReciboHonorarioInspector,
  reciboHonorarioInspectorSchema,
} from "../schemas/recibo-honorario.schema";

const responseSchema = apiResponseSchema(reciboHonorarioInspectorSchema);
type ResponseType = {
  success: boolean;
  data: ReciboHonorarioInspector | null;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  } | null;
};

export function useCrearReciboInspector() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    ResponseType,
    { liquidacion_inspector_id: string; inspecciones_mes: number }
  >({
    url: "/finanzas/recibos-inspectores",
    schema: responseSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["finanzas", "recibos-inspectores"],
        });
      },
    },
  });

  return mutation;
}
