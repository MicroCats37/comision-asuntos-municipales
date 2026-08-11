/**
 * Hook para detalle de liquidación de Mecánica de Suelos.
 * Endpoint: GET /liquidaciones/mecanica-suelos/{id}
 */
import { useApiQuery } from "@/hooks";
import { liquidacionMecanicaSuelosDetailResponseSchema } from "@/features_deprecated/liquidaciones/schemas/liquidacion-mecanica-suelos.schema";

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
      select: (data) => data.data ?? null,
      enabled: !!id,
    },
  });

  return {
    ...query,
    data: query.data ?? null,
  };
}
