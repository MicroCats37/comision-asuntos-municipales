/**
 * Hook para detalle de liquidación de Edificaciones.
 * Endpoint: GET /liquidaciones/edificaciones/{id}
 * Devuelve el detalle 3-wrappers (liquidacion_general/liquidacion_especifica/liquidacion_tipo).
 */
import { useApiQuery } from "@/hooks";
import {
  liquidacionEdificacionesDetalleResponseSchema,
  type LiquidacionEdificacionesDetalleItem,
} from "../schemas/liquidacion-edificaciones.schema";

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
    // Schema PROPIO de Edificaciones: conserva estrategia, snapshots y
    // acumulación. El wrapper PO compartido no se toca (Taludes / IV / edge).
    schema: liquidacionEdificacionesDetalleResponseSchema,
    queryOptions: {
      select: (response): LiquidacionEdificacionesDetalleItem | null => {
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
