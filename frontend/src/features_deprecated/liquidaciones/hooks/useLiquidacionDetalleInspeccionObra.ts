/**
 * Hook para detalle de liquidación de Inspección de Obra.
 * Endpoint: GET /liquidaciones/inspeccion-obra/{id}
 */
import { useApiQuery } from "@/hooks";
import { inspeccionObraService } from "../services/inspeccion-obra.service";
import { liquidacionInspeccionObraDetailResponseSchema } from "../schemas/liquidacion-inspeccion-obra.schema";
import type { LiquidacionInspeccionObraListItem } from "../types/liquidacion-inspeccion-obra.types";

interface UseLiquidacionDetalleInspeccionObraProps {
  id: string;
}

export function useLiquidacionDetalleInspeccionObra({
  id,
}: UseLiquidacionDetalleInspeccionObraProps) {
  const queryKey = ["liquidaciones", "inspeccion-obra", "detalle", id];

  const query = useApiQuery({
    queryKey,
    url: id ? `/liquidaciones/inspeccion-obra/${id}` : null,
    schema: liquidacionInspeccionObraDetailResponseSchema,
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
