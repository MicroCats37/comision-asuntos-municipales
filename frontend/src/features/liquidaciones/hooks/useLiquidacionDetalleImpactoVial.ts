/**
 * Hook para detalle de liquidación de Impacto Vial.
 * Endpoint: GET /liquidaciones/impacto-vial/{id}
 * Devuelve el detalle 3-wrappers tipado por liquidacionImpactoVialDetailResponseSchema.
 */
import { useApiQuery } from "@/hooks";
import {
  type LiquidacionDetalleItem,
  liquidacionImpactoVialDetailResponseSchema,
} from "../schemas/liquidacion-detail.schemas";

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
      select: (data): LiquidacionDetalleItem | null => data.data ?? null,
      enabled: !!id,
    },
  });

  return {
    ...query,
    data: query.data ?? null,
  };
}
