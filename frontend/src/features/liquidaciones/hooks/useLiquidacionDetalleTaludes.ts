/**
 * Hook para detalle de liquidación de Taludes.
 * Endpoint: GET /liquidaciones/taludes/{id}
 */
import { useApiQuery } from "@/hooks";
import { taludesService } from "../services/taludes.service";
import { liquidacionTaludesDetailResponseSchema } from "../schemas/liquidacion-taludes.schema";
import type { LiquidacionTaludesListItem } from "../types/liquidacion-taludes.types";

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
      select: (data) => data.data ?? null,
      enabled: !!id,
    },
  });

  return {
    ...query,
    data: query.data ?? null,
  };
}
