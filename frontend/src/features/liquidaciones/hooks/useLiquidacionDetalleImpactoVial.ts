/**
 * Hook para detalle de liquidación de Impacto Vial.
 * Endpoint: GET /liquidaciones/impacto-vial/{id}
 */
import { useApiQuery } from "@/hooks";
import { liquidacionImpactoVialDetailResponseSchema } from "@/features_deprecated/liquidaciones/schemas/liquidacion-impacto-vial.schema";

interface UseLiquidacionDetalleImpactoVialProps {
  id: string;
}

export function useLiquidacionDetalleImpactoVial({
  id,
}: UseLiquidacionDetalleImpactoVialProps) {
  const queryKey = ["liquidaciones", "impacto-vial", "detalle", id];

  const query = useApiQuery({
    queryKey,
    url: id ? `/liquidaciones/impacto-vial/${id}` : null,
    schema: liquidacionImpactoVialDetailResponseSchema,
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
