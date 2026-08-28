/**
 * Hook para detalle de liquidación de Taludes.
 * Endpoint: GET /liquidaciones/taludes/{id}
 * Devuelve el detalle 3-wrappers tipado por liquidacionTaludesDetailResponseSchema.
 */
import { useApiQuery } from "@/hooks";
import {
  type LiquidacionDetalleItem,
  liquidacionTaludesDetailResponseSchema,
} from "../schemas/liquidacion-detail.schemas";

interface UseLiquidacionDetalleTaludesProps {
  id: string;
}

export function useLiquidacionDetalleTaludes({
  id,
}: UseLiquidacionDetalleTaludesProps) {
  const queryKey = ["liquidaciones", "taludes", "detalle", id];

  const query = useApiQuery({
    queryKey,
    url: id ? `/liquidaciones/taludes/${id}` : null,
    schema: liquidacionTaludesDetailResponseSchema,
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
