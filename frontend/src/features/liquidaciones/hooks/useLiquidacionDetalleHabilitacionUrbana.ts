/**
 * Hook para detalle de liquidación de Habilitación Urbana.
 * Endpoint: GET /liquidaciones/habilitacion-urbana/{id}
 * Devuelve el detalle 3-wrappers tipado por liquidacionHabilitacionUrbanaDetailResponseSchema.
 */
import { useApiQuery } from "@/hooks";
import {
  type LiquidacionDetalleItem,
  liquidacionHabilitacionUrbanaDetailResponseSchema,
} from "../schemas/liquidacion-detail.schemas";

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
      select: (data): LiquidacionDetalleItem | null => data.data ?? null,
      enabled: !!id,
    },
  });

  return {
    ...query,
    data: query.data ?? null,
  };
}
