/**
 * Hook para "Ver detalle" de una candidata de Inspector.
 * Usa el endpoint GET /liquidaciones/inspeccion-obra/{liquidacion_categoria_visitas_id}
 * y devuelve LiquidacionDetalleItem.
 *
 * No hace nada si id es null/undefined/blank.
 */
import { useLiquidacionDetalleInspeccionObra } from "@/features/liquidaciones/hooks/useLiquidacionDetalleInspeccionObra";
import type { LiquidacionDetalleItem } from "@/features/liquidaciones/schemas/liquidacion-detail.schemas";

interface UseVerDetalleInspectorProps {
  id: string | null | undefined;
}

export function useVerDetalleInspector({ id }: UseVerDetalleInspectorProps) {
  return useLiquidacionDetalleInspeccionObra({ id: id ?? "" });
}

export type UseVerDetalleInspectorData = LiquidacionDetalleItem | null;
