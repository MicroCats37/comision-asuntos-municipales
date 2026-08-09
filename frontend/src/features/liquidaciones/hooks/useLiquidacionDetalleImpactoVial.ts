/**
 * Hook para detalle de liquidación de Impacto Vial.
 * Endpoint: GET /liquidaciones/impacto-vial/{id}
 */
import { useApiQuery } from "@/hooks";
import { impactoVialService } from "../services/impacto-vial.service";
import { liquidacionImpactoVialDetailResponseSchema } from "../schemas/liquidacion-impacto-vial.schema";
import type { LiquidacionImpactoVialListItem } from "../types/liquidacion-impacto-vial.types";

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
