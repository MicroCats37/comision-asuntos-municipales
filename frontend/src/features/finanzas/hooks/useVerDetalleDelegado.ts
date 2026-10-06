/**
 * Hook para "Ver detalle" de una candidata de Delegado.
 *
 * Dispatch based on tipo_liquidacion.codigo:
 *   EDIFICACION         → GET /liquidaciones/edificaciones/{id}
 *   HABILITACION_URBANA → GET /liquidaciones/habilitacion-urbana/{id}
 *   MECANICA_SUELOS     → GET /liquidaciones/mecanica-suelos/{id}
 *   TALUDES             → GET /liquidaciones/taludes/{id}
 *   IMPACTO_VIAL        → GET /liquidaciones/impacto-vial/{id}
 *   INSPECCION_OBRA     → GET /liquidaciones/inspeccion-obra/{id}
 *
 * Returns LiquidacionDetalleItem | null.
 * Returns null when id or tipo_codigo is missing/unsupported.
 */
import { useLiquidacionDetalleEdificacion } from "@/features/liquidaciones/hooks/useLiquidacionDetalleEdificacion";
import { useLiquidacionDetalleHabilitacionUrbana } from "@/features/liquidaciones/hooks/useLiquidacionDetalleHabilitacionUrbana";
import { useLiquidacionDetalleImpactoVial } from "@/features/liquidaciones/hooks/useLiquidacionDetalleImpactoVial";
import { useLiquidacionDetalleInspeccionObra } from "@/features/liquidaciones/hooks/useLiquidacionDetalleInspeccionObra";
import { useLiquidacionDetalleMecanicaSuelos } from "@/features/liquidaciones/hooks/useLiquidacionDetalleMecanicaSuelos";
import { useLiquidacionDetalleTaludes } from "@/features/liquidaciones/hooks/useLiquidacionDetalleTaludes";
import type { LiquidacionDetalleItem } from "@/features/liquidaciones/schemas/liquidacion-detail.schemas";

interface UseVerDetalleDelegadoProps {
  id: string | null | undefined;
  tipoCodigo: string | null | undefined;
}

/**
 * Unified detail hook that dispatches to the correct typed detail hook
 * based on tipo_liquidacion.codigo.
 */
export function useVerDetalleDelegado({
  id,
  tipoCodigo,
}: UseVerDetalleDelegadoProps) {
  // EDIFICACION
  if (tipoCodigo === "EDIFICACION") {
    return useLiquidacionDetalleEdificacion({ id: id ?? "" });
  }
  // HABILITACION_URBANA
  if (tipoCodigo === "HABILITACION_URBANA") {
    return useLiquidacionDetalleHabilitacionUrbana({ id: id ?? "" });
  }
  // MECANICA_SUELOS
  if (tipoCodigo === "MECANICA_SUELOS") {
    return useLiquidacionDetalleMecanicaSuelos({ id: id ?? "" });
  }
  // TALUDES
  if (tipoCodigo === "TALUDES") {
    return useLiquidacionDetalleTaludes({ id: id ?? "" });
  }
  // IMPACTO_VIAL
  if (tipoCodigo === "IMPACTO_VIAL") {
    return useLiquidacionDetalleImpactoVial({ id: id ?? "" });
  }
  // INSPECCION_OBRA
  if (tipoCodigo === "INSPECCION_OBRA") {
    return useLiquidacionDetalleInspeccionObra({ id: id ?? "" });
  }

  // Unsupported or missing tipo — return a placeholder that callers handle as "no data".
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return undefined as any;
}

export type UseVerDetalleDelegadoData = LiquidacionDetalleItem | null;
