"use client";

import { Maximize2 } from "lucide-react";

/**
 * Minimal shape that HU/MS liquidacion_tipo satisfies — both expose
 * `area_m2` plus optional descriptive specialty fields. Loose typing keeps
 * the cell reusable.
 */
export interface AreaLike {
  area_m2?: number | null;
}

/**
 * Cell showing `area_m2` (área en m²). Inline, prominent — single value
 * per row, no chips or tooltips needed.
 */
export function AreaCell({ lt }: { lt: AreaLike }) {
  const area = lt.area_m2;

  return (
    <div className="flex flex-col gap-0.5 justify-center items-center text-center px-3 py-3.5 min-w-0">
      <div className="flex items-baseline gap-1.5 justify-center w-full">
        <Maximize2 className="h-3 w-3 text-muted-foreground/60 shrink-0" />
        <span className="text-base font-black text-primary tabular-nums leading-tight">
          {area != null ? area.toLocaleString("es-PE") : "—"}
        </span>
        <span className="text-[10px] font-semibold text-muted-foreground/70 uppercase">
          m²
        </span>
      </div>
    </div>
  );
}
