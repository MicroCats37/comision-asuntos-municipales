/**
 * Hook para detalle de liquidación de Inspección de Obra.
 * Endpoint: GET /liquidaciones/inspeccion-obra/{id}
 */
import { useApiQuery } from "@/hooks";
import { liquidacionInspeccionObraDetailResponseSchema } from "@/features_deprecated/liquidaciones/schemas/liquidacion-inspeccion-obra.schema";

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
