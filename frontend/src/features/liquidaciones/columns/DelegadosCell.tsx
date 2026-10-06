"use client";

import { Users } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * Minimal shape that every liquidacion list item's `delegados` array
 * satisfies (LiquidacionDelegadoEnGeneralOutput from
 * schemas/liquidacion-base.schema.ts). Loose typing keeps the cell reusable.
 */
export interface DelegadoLike {
  datos?: {
    dictamen_revision?: string | null;
  };
  delegado?: {
    id?: string;
    nombre_completo?: string;
    cip?: string;
    tipo?: string;
    especialidad?: { id?: string; nombre?: string };
  };
}

interface DelegadosCellProps {
  delegados?: DelegadoLike[] | null;
}

/**
 * Strip the redundant "Ingeniería" prefix from especialidad nombres.
 * "Ingeniería Civil" → "Civil". Internal "Ingeniería" occurrences
 * (e.g. "Ingeniería Eléctrica y Mecánica") are kept intact.
 */
function stripIngenieriaPrefix(name: string): string {
  if (!name) return name;
  const stripped = name.replace(/^ingenier[ií]a\s+/i, "").trim();
  return stripped || name;
}

/**
 * Numbered list of delegates, one row per delegado inside a chip-style
 * wrapper (bg-secondary + border) so each especialidad stands out at
 * a glance. Hover reveals nombre_completo + tipo + dictamen.
 */
export function DelegadosCell({ delegados }: DelegadosCellProps) {
  const list = delegados ?? [];

  if (list.length === 0) {
    return (
      <div className="flex items-center justify-start px-3 py-3.5">
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground/50">
          <Users className="h-3 w-3" />
          Sin
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 justify-center px-3 py-3 min-w-0">
      {list.map((d, i) => {
        const cip = d.delegado?.cip;
        const esp = stripIngenieriaPrefix(
          d.delegado?.especialidad?.nombre ?? "Sin esp.",
        );
        const nombre = d.delegado?.nombre_completo;
        const tipo = d.delegado?.tipo;
        const dictamen = d.datos?.dictamen_revision;
        const key = d.delegado?.id ?? `d-${i}`;
        return (
          <Tooltip key={key}>
            <TooltipTrigger asChild>
              <button
                type="button"
                className="text-left flex items-center gap-1.5 rounded-md bg-secondary/40 border border-secondary/50 px-2 py-0.5 text-[10px] hover:bg-secondary/60 transition-colors min-w-0 w-full"
              >
                <span className="font-semibold uppercase tracking-wide text-foreground/90 [text-wrap:pretty] flex-1 min-w-0 truncate">
                  {esp}
                </span>
                <span className="font-mono font-bold text-primary tabular-nums shrink-0">
                  CIP {cip ?? "—"}
                </span>
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={6} className="max-w-xs">
              {nombre && (
                <div className="font-semibold text-foreground text-xs">
                  {nombre}
                </div>
              )}
              {tipo && (
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">
                  Tipo: {tipo}
                </div>
              )}
              {dictamen && (
                <div className="font-mono text-[10px] text-muted-foreground mt-0.5">
                  Dictamen {dictamen}
                </div>
              )}
              {esp && (
                <div className="text-[10px] text-muted-foreground/80 mt-1 italic">
                  {esp}
                </div>
              )}
            </TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}
