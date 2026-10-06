"use client";

import { ClipboardList } from "lucide-react";

/**
 * Minimal shape that IO (Inspección de Obra) liquidacion_tipo satisfies.
 */
export interface VisitasLike {
  cantidad_visitas?: number | null;
  categoria?: string | null;
}

/**
 * Cell showing `cantidad_visitas` (count badge) + `categoria` (label).
 * Inspectores go in a separate column (`InspectoresCell`).
 */
export function VisitasCell({ lt }: { lt: VisitasLike }) {
  const count = lt.cantidad_visitas;
  const categoria = lt.categoria;

  return (
    <div className="flex flex-col gap-1 justify-center items-center text-center px-3 py-3.5 min-w-0">
      <div className="inline-flex w-fit items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-bold uppercase tracking-wider text-primary">
        <ClipboardList className="h-3 w-3 shrink-0" />
        <span className="tabular-nums">{count ?? 0}</span>
        <span className="text-[10px] text-primary/80">visitas</span>
      </div>
      {categoria ? (
        <span className="inline-flex w-fit items-center rounded bg-secondary px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-secondary-foreground">
          {categoria}
        </span>
      ) : null}
    </div>
  );
}
