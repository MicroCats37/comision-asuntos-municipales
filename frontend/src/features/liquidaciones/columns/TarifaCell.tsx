"use client";

import { Scale } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { formatDecimalPercent } from "@/utils/number-formatter";
import { formatCurrency } from "../components/liquidacion-ui";
import type { PorcentajeObraDatosOut } from "../schemas/liquidacion-porcentaje.schema";

interface TarifaCellProps {
  lt: PorcentajeObraDatosOut;
}

/**
 * Strip the redundant "Ingeniería" prefix the backend prepends.
 * "Ingeniería Civil" → "Civil". Internal "Ingeniería" occurrences
 * (e.g. "Ingeniería Eléctrica y Mecánica") are kept intact.
 */
function stripIngenieriaPrefix(name: string): string {
  if (!name) return name;
  const stripped = name.replace(/^ingenier[ií]a\s+/i, "").trim();
  return stripped || name;
}

/**
 * Cell that lists every `detalle` as a chip (matching DelegadosCell's
 * chip pattern). The entire cell is the TooltipTrigger — hover reveals
 * the global breakdown (every tarifa with % + subtotal, plus sum).
 */
export function TarifaCell({ lt }: TarifaCellProps) {
  const detalles = lt.detalles ?? [];

  if (detalles.length === 0) {
    return (
      <div className="flex items-center justify-start px-3 py-3.5">
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground/50">
          <Scale className="h-3 w-3" />
          Sin
        </span>
      </div>
    );
  }

  const subtotalSum = detalles.reduce((acc, d) => acc + (d.subtotal ?? 0), 0);

  return (
    <div className="flex items-center justify-center px-3 py-3 min-w-0">
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex flex-col gap-1 min-w-0 w-full cursor-pointer">
            {detalles.map((d) => (
              <div
                key={d.id}
                className="text-left flex items-center gap-1.5 rounded-md bg-secondary/40 border border-secondary/50 px-2 py-0.5 text-[10px] min-w-0 w-full"
              >
                <span className="font-semibold uppercase tracking-wide text-foreground/90 [text-wrap:pretty] flex-1 min-w-0 truncate">
                  {stripIngenieriaPrefix(d.especialidad?.nombre ?? "Tarifa")}
                </span>
                <span className="font-mono font-bold text-primary tabular-nums shrink-0">
                  {formatDecimalPercent(d.porcentaje_aplicado)}
                </span>
              </div>
            ))}
          </div>
        </TooltipTrigger>
        <TooltipContent
          side="right"
          sideOffset={6}
          className="p-0 max-w-xs overflow-hidden"
        >
          <div className="bg-popover text-popover-foreground rounded-md border shadow-md">
            <div className="px-3 py-2 border-b bg-muted/40 text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center justify-between gap-4">
              <span>Tarifas aplicadas ({detalles.length})</span>
              <span className="font-semibold text-foreground tabular-nums">
                = {formatCurrency(subtotalSum)}
              </span>
            </div>
            <div className="divide-y divide-border/40 max-h-80 overflow-y-auto">
              {detalles.map((d) => (
                <div
                  key={d.id}
                  className="grid grid-cols-[1fr_auto_auto] gap-x-3 px-3 py-1.5 text-[11px] items-baseline"
                >
                  <span className="truncate">
                    {stripIngenieriaPrefix(d.especialidad?.nombre ?? "Tarifa")}
                  </span>
                  <span className="font-semibold text-primary tabular-nums">
                    {formatDecimalPercent(d.porcentaje_aplicado)}
                  </span>
                  <span className="font-semibold tabular-nums">
                    {formatCurrency(d.subtotal)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </div>
  );
}
