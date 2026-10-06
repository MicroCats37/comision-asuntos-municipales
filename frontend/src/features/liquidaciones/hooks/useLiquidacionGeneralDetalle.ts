/**
 * Hook para detalle de liquidación general (polimórfico).
 * Endpoint: GET /liquidaciones/generales/{id}/detalle
 *
 * Devuelve el detalle 3-wrappers: liquidacion_general + liquidacion_especifica + liquidacion_tipo.
 * El tipo de liquidacion_tipo se determina por el codigo en liquidacion_general.tipo_liquidacion.codigo.
 *
 * Reemplaza los hooks tipo-específicos (useLiquidacionDetalleEdificacion, etc.) y los
 * hooks de dispatch (useVerDetalleDelegado, useVerDetalleInspector) en el contexto de los
 * modales RH mensual.
 */
import type { LiquidacionDetalleItem } from "@/features/liquidaciones/schemas/liquidacion-detail.schemas";
import { liquidacionEdificacionOutResponseSchema } from "@/features/liquidaciones/schemas/liquidacion-detail.schemas";
import { useApiQuery } from "@/hooks";

interface UseLiquidacionGeneralDetalleProps {
  id: string | null | undefined;
}

/**
 * Unified detail hook — calls GET /liquidaciones/generales/{id}/detalle
 * which returns the polymorphic LiquidacionDetalleItem structure regardless of tipo.
 */
export function useLiquidacionGeneralDetalle({
  id,
}: UseLiquidacionGeneralDetalleProps) {
  const queryKey = ["liquidaciones", "generales", "detalle", id];

  const query = useApiQuery({
    queryKey,
    url: id ? `/liquidaciones/generales/${id}/detalle` : null,
    schema: liquidacionEdificacionOutResponseSchema,
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
