"use client";

import { Percent } from "lucide-react";

interface Props {
  /** Visit percentage from `VisitasDatosOut.porcentaje_uit` (decimal 0-100). */
  porcentaje_uit: number | null | undefined;
}

/**
 * Cell showing the visit percentage from `VisitasDatosOut.porcentaje_uit`.
 * Compact percentage chip — pairs naturally with `VisitasCell` (count).
 */
export function VisitasPorcentajeCell({ porcentaje_uit }: Props) {
  if (porcentaje_uit == null) return null;

  const formatted = new Intl.NumberFormat("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(porcentaje_uit);

  return (
    <div className="flex flex-col justify-center items-center text-center gap-0.5 px-3 py-3.5 min-w-0">
      <div className="flex items-baseline gap-1.5 justify-center w-full">
        <Percent className="h-3 w-3 text-muted-foreground/60 shrink-0" />
        <span className="text-sm font-bold text-primary tabular-nums">
          {formatted} UIT
        </span>
      </div>
    </div>
  );
}
