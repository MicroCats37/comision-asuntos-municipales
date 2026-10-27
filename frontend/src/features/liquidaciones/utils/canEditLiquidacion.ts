/**
 * Editability helpers for liquidaciones.
 *
 * La regla PAGADA se mantiene: liquidaciones pagadas no son editables.
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
      reason: "La liquidacion ya fue pagada",
    };
  }

  const canEditProyecto = true;

  return {
    canEdit: true,
    canEditProyecto,
    reason: undefined,
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
