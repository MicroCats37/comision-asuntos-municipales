"use client";

import { Banknote } from "lucide-react";

interface Props {
  /** Rate per m² from backend (M2DatosOut.costo_por_m2). */
  costo_por_m2: number | null | undefined;
}

/**
 * Cell showing the rate per m² (`costo_por_m2` from M2DatosOut). Comes
 * directly from backend — not derived — to match the authoritative
 * tariff amount that determines derechos mínimos / máximos.
 */
export function TarifaMCell({ costo_por_m2 }: Props) {
  if (costo_por_m2 == null) return null;

  const formatted = new Intl.NumberFormat("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(costo_por_m2);

  return (
    <div className="flex flex-col justify-center items-center text-center gap-0.5 px-3 py-3.5 min-w-0">
      <div className="flex items-baseline gap-1.5 justify-center w-full">
        <Banknote className="h-3 w-3 text-muted-foreground/60 shrink-0" />
        <span className="text-sm font-bold text-primary tabular-nums">
          S/ {formatted}
        </span>
      </div>
    </div>
  );
}
