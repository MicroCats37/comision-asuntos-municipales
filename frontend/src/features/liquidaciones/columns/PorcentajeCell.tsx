"use client";

import { formatDecimalPercent } from "@/utils/number-formatter";
import type { PorcentajeObraDatosOut } from "../schemas/liquidacion-porcentaje.schema";

interface PorcentajeCellProps {
  /** PorcentajeObra data (Edif / IV / Taludes) */
  lt: PorcentajeObraDatosOut;
  /** Optional badge above the % (e.g. "AMPLIACIÓN" for Edif). */
  tipoTramiteLabel?: string;
}

/**
 * Single cell showing the % Liquidación as the primary visual.
 *
 * Header context (provided by `extraColumns[…].header`) carries the unit —
 * "% Liq." — so the cell just shows the number.
 */
export function PorcentajeCell({ lt, tipoTramiteLabel }: PorcentajeCellProps) {
  return (
    <div className="flex flex-col gap-1 justify-center px-3 py-3.5 min-w-0">
      {tipoTramiteLabel && (
        <span className="inline-flex w-fit items-center rounded-md bg-secondary text-secondary-foreground/85 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider">
          {tipoTramiteLabel}
        </span>
      )}
      <span className="text-base font-black text-primary tracking-tight leading-none tabular-nums">
        {formatDecimalPercent(lt.porcentaje_liquidacion)}
      </span>
    </div>
  );
}
