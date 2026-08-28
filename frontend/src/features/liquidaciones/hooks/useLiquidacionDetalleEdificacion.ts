/**
 * Hook para detalle de liquidación de Edificaciones.
 * Endpoint: GET /liquidaciones/edificaciones/{id}
 * Devuelve el detalle 3-wrappers (liquidacion_general/liquidacion_especifica/liquidacion_tipo).
 */
import { useApiQuery } from "@/hooks";
import {
  type LiquidacionEdificacionOut,
  liquidacionEdificacionOutResponseSchema,
} from "../schemas/liquidacion-detail.schemas";

interface UseLiquidacionDetalleEdificacionProps {
  id: string;
}

export function useLiquidacionDetalleEdificacion({
  id,
}: UseLiquidacionDetalleEdificacionProps) {
  const queryKey = ["liquidaciones", "edificaciones", "detalle", id];

  const query = useApiQuery({
    queryKey,
    url: id ? `/liquidaciones/edificaciones/${id}` : null,
    schema: liquidacionEdificacionOutResponseSchema,
    queryOptions: {
      select: (response): LiquidacionEdificacionOut | null => {
        return response.data ?? null;
      },
      enabled: !!id,
    },
  });

  return {
    ...query,
    data: query.data ?? null,
  };
}
