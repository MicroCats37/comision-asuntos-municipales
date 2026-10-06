"use client";

/**
 * RhInspectorVariablesCalculo — Displays RH calculation percentage/range variables
 * for Inspector variant.
 *
 * @param escala_nombre     - Optional scale name
 * @param porcentaje_descuento - Percentage as fraction, e.g. 0.20
 * @param monto_minimo      - Optional minimum amount
 * @param monto_maximo      - Optional maximum amount
 * @param compact           - If true, renders smaller text suitable for cards.
 */

import React from "react";

export interface RhInspectorVariablesCalculoProps {
  escala_nombre?: string;
  /** Percentage as fraction, e.g. 0.20 */
  porcentaje_descuento: number;
  monto_minimo?: number;
  monto_maximo?: number;
  compact?: boolean;
}

export function RhInspectorVariablesCalculo({
  escala_nombre,
  porcentaje_descuento,
  monto_minimo,
  monto_maximo,
  compact = false,
}: RhInspectorVariablesCalculoProps) {
  const pctDescuento = (porcentaje_descuento * 100).toFixed(0);

  // Build range label if both bounds are available
  let rangeLabel = "";
  if (monto_minimo != null && monto_maximo != null) {
    rangeLabel = ` (S/ ${monto_minimo.toLocaleString()} – S/ ${monto_maximo.toLocaleString()})`;
  } else if (monto_minimo != null) {
    rangeLabel = ` (desde S/ ${monto_minimo.toLocaleString()})`;
  }

  if (compact) {
    return (
      <div className="text-[10px] text-muted-foreground">
        <span className="font-semibold">Desc. </span>
        <span>
          {pctDescuento}%{rangeLabel}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground border-t border-primary/10 pt-2 mt-1">
      <span className="font-semibold">Escala: {escala_nombre || "—"}</span>
      <span>
        Descuento aplicado {pctDescuento}%{rangeLabel}
      </span>
    </div>
  );
}
