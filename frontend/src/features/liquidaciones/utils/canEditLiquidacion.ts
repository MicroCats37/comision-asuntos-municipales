/**
 * Editability helpers for liquidaciones.
 *
 * Rules:
 * - PAGADA liquidaciones cannot be edited at all.
 * - Proyecto/municipalidad/entity fields can only be edited when:
 *   numero_revision === 1 AND no liquidaciones_previas.
 */
import type { LiquidacionGeneralOutput } from "../schemas/liquidacion-base.schema";

export interface CanEditLiquidacionResult {
  canEdit: boolean;
  canEditProyecto: boolean;
  reason?: string;
}

/**
 * Returns whether the liquidacion can be edited and whether proyecto fields
 * are editable.
 *
 * @param lg - The liquidacion_general wrapper from card/detail data
 */
export function canEditLiquidacion(
  lg: LiquidacionGeneralOutput,
): CanEditLiquidacionResult {
  if (lg.estado === "PAGADA") {
    return {
      canEdit: false,
      canEditProyecto: false,
      reason: "La liquidación ya fue pagada",
    };
  }

  const canEditProyecto =
    lg.numero_revision === 1 && !lg.liquidaciones_previas?.length;

  return {
    canEdit: true,
    canEditProyecto,
    reason: canEditProyecto
      ? undefined
      : "El proyecto no es editable en revisiones posteriores",
  };
}

/**
 * Shortcut: true only when proyecto fields are editable.
 * Convenience wrapper for conditional rendering of proyecto field groups.
 */
export function canEditProyectoLiquidacion(
  lg: LiquidacionGeneralOutput,
): boolean {
  return canEditLiquidacion(lg).canEditProyecto;
}
