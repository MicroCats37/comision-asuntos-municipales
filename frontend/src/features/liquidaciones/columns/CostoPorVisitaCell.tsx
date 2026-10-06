"use client";

import { Banknote } from "lucide-react";
import { formatCurrency } from "../components/liquidacion-ui";

interface Props {
  /** UIT value (S/) from `lg.uit.valor`. */
  uit: number | null | undefined;
  /** Visit proportion (0-1 range, e.g. 0.05 for 5 %) from `lt.porcentaje_uit`. */
  porcentaje_uit: number | null | undefined;
}

/**
 * Cell showing `UIT × porcentaje_uit` — the cost per visit.
 * `porcentaje_uit` is already a proportion (decimal 0-1 range, e.g. 0.05
 * for 5 %), so no division by 100 is needed.
 * Returns null when either input is missing.
 */
export function CostoPorVisitaCell({ uit, porcentaje_uit }: Props) {
  if (uit == null || porcentaje_uit == null) return null;

  const costo = uit * porcentaje_uit;

  return (
    <div className="flex flex-col justify-center items-center text-center gap-0.5 px-3 py-3.5 min-w-0">
      <div className="flex items-baseline gap-1.5 justify-center w-full">
        <Banknote className="h-3 w-3 text-muted-foreground/60 shrink-0" />
        <span className="text-sm font-bold text-primary tabular-nums">
          {formatCurrency(costo)}
        </span>
      </div>
    </div>
  );
}
