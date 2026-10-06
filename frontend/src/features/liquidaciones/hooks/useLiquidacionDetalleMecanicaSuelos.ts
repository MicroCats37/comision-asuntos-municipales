/**
 * Hook para detalle de liquidación de Mecánica de Suelos.
 * Endpoint: GET /liquidaciones/mecanica-suelos/{id}
 * Devuelve el detalle 3-wrappers tipado por liquidacionMecanicaSuelosDetailResponseSchema.
 */
import { useApiQuery } from "@/hooks";
import {
  type LiquidacionDetalleItem,
  liquidacionMecanicaSuelosDetailResponseSchema,
} from "../schemas/liquidacion-detail.schemas";

interface UseLiquidacionDetalleMecanicaSuelosProps {
  id: string;
}

export function useLiquidacionDetalleMecanicaSuelos({
  id,
}: UseLiquidacionDetalleMecanicaSuelosProps) {
  const queryKey = ["liquidaciones", "mecanica-suelos", "detalle", id];

  const query = useApiQuery({
    queryKey,
    url: id ? `/liquidaciones/mecanica-suelos/${id}` : null,
    schema: liquidacionMecanicaSuelosDetailResponseSchema,
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
