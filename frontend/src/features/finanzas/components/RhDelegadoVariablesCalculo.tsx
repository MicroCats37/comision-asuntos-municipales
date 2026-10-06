"use client";

/**
 * RhDelegadoVariablesCalculo — Displays RH calculation tasa/percentage variables
 * for Delegado variant.
 *
 * @param tasa_renta_cip    - Rate as fraction, e.g. 0.25
 * @param tasa_aporte_codemu - Rate as fraction, e.g. 0.05
 * @param tasa_fondo_comun  - Rate as fraction, e.g. 0.10
 * @param compact            - If true, renders smaller text suitable for cards.
 */

import React from "react";

export interface RhDelegadoVariablesCalculoProps {
  /** Rate as fraction, e.g. 0.25 */
  tasa_renta_cip: number;
  /** Rate as fraction, e.g. 0.05 */
  tasa_aporte_codemu: number;
  /** Rate as fraction, e.g. 0.10 */
  tasa_fondo_comun: number;
  compact?: boolean;
}

export function RhDelegadoVariablesCalculo({
  tasa_renta_cip,
  tasa_aporte_codemu,
  tasa_fondo_comun,
  compact = false,
}: RhDelegadoVariablesCalculoProps) {
  const pctRenta = (tasa_renta_cip * 100).toFixed(0);
  const pctAporte = (tasa_aporte_codemu * 100).toFixed(0);
  const pctFondo = (tasa_fondo_comun * 100).toFixed(0);

  if (compact) {
    return (
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-muted-foreground">
        <span>CIP {pctRenta}%</span>
        <span>Aporte CODEMU {pctAporte}%</span>
        <span>Fondo común {pctFondo}%</span>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground border-t border-primary/10 pt-2 mt-1">
      <span className="font-semibold">Tasas aplicadas:</span>
      <span>CIP {pctRenta}%</span>
      <span>Aporte CODEMU {pctAporte}%</span>
      <span>Fondo común {pctFondo}%</span>
    </div>
  );
}
