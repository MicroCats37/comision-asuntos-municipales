/**
 * Hook para detalle de liquidación de Habilitación Urbana.
 * Endpoint: GET /liquidaciones/habilitacion-urbana/{id}
 */
import { useApiQuery } from "@/hooks";
import { liquidacionHabilitacionUrbanaDetailResponseSchema } from "../schemas/liquidacion-detail.schemas";

interface UseLiquidacionDetalleHabilitacionUrbanaProps {
  id: string;
}

export function useLiquidacionDetalleHabilitacionUrbana({
  id,
}: UseLiquidacionDetalleHabilitacionUrbanaProps) {
  const queryKey = ["liquidaciones", "habilitacion-urbana", "detalle", id];

  const query = useApiQuery({
    queryKey,
    url: id ? `/liquidaciones/habilitacion-urbana/${id}` : null,
    schema: liquidacionHabilitacionUrbanaDetailResponseSchema,
    queryOptions: {
      select: (data) => data.data ?? null,
      enabled: !!id,
    },
  });

  return {
    ...query,
    data: query.data ?? null,
  };
}
