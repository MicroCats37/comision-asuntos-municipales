/**
 * Hook para detalle de liquidación de Inspección de Obra.
 * Endpoint: GET /liquidaciones/inspeccion-obra/{id}
 * Devuelve el detalle 3-wrappers tipado por liquidacionInspeccionObraDetailResponseSchema.
 */
import { useApiQuery } from "@/hooks";
import {
  type LiquidacionDetalleItem,
  liquidacionInspeccionObraDetailResponseSchema,
} from "../schemas/liquidacion-detail.schemas";

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
      select: (data): LiquidacionDetalleItem | null => data.data ?? null,
      enabled: !!id,
    },
  });

  return {
    ...query,
    data: query.data ?? null,
  };
}
