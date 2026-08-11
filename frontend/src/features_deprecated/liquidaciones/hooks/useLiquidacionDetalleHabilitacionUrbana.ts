/**
 * Hook para detalle de liquidación de Habilitación Urbana.
 * Endpoint: GET /liquidaciones/habilitacion-urbana/{id}
 */
import { useApiQuery } from "@/hooks";
import { habilitacionUrbanaService } from "../services/habilitacion-urbana.service";
import { liquidacionHabilitacionUrbanaDetailResponseSchema } from "../schemas/liquidacion-habilitacion-urbana.schema";
import type { LiquidacionHabilitacionUrbanaListItem } from "../types/liquidacion-habilitacion-urbana.types";

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
