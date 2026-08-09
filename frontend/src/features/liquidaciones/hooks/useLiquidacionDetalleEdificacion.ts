/**
 * Hook para detalle de liquidación de Edificaciones.
 * Endpoint: GET /liquidaciones/edificaciones/{id}
 */
import { useApiQuery } from "@/hooks";
import { liquidacionesEdificacionesService } from "../services/liquidaciones-edificaciones.service";
import type { LiquidacionEdificacionOut } from "../types/liquidacion-edificaciones";
import { liquidacionEdificacionOutResponseSchema } from "../schemas/liquidacion.schema";

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
        const apiResponse = response as { success: boolean; data: LiquidacionEdificacionOut };
        return apiResponse?.data ?? null;
      },
      enabled: !!id,
    },
  });

  return {
    ...query,
    data: query.data ?? null,
  };
}
