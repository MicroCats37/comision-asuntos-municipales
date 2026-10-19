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
 * wrapper (bg-secondary + border) so each especialidad stands out at a
 * glance. The whole cell triggers a single consolidated tooltip listing
 * every delegate with their full name, tipo + dictamen — fixes the prior
 * "n tooltips overlap on hover" / "name missing" UX issues.
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
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <div className="flex flex-col gap-1 justify-center px-3 py-3 min-w-0 cursor-help">
          {list.map((d, i) => {
            const cip = d.delegado?.cip;
            const esp = stripIngenieriaPrefix(
              d.delegado?.especialidad?.nombre ?? "Sin esp.",
            );
            const key = d.delegado?.id ?? `d-${i}`;
            return (
              <button
                key={key}
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
            );
          })}
        </div>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={6}
        className="max-w-sm p-3 bg-popover text-popover-foreground border border-border"
      >
        <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
          Delegados ({list.length})
        </p>
        <ul className="space-y-1.5">
          {list.map((d, i) => {
            const nombre = d.delegado?.nombre_completo ?? "Sin nombre";
            const tipo = d.delegado?.tipo;
            const cip = d.delegado?.cip;
            const esp = stripIngenieriaPrefix(
              d.delegado?.especialidad?.nombre ?? "Sin esp.",
            );
            const dictamen = d.datos?.dictamen_revision;
            const key = d.delegado?.id ?? `d-${i}`;
            return (
              <li key={key} className="flex flex-col gap-0.5">
                <span className="text-sm font-semibold text-foreground leading-tight">
                  {nombre}
                </span>
                <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-muted-foreground">
                  {tipo ? (
                    <span className="inline-flex items-center rounded bg-primary/10 px-1 py-0.5 font-bold uppercase tracking-wider text-primary">
                      {tipo}
                    </span>
                  ) : null}
                  {cip ? <span className="font-mono">CIP {cip}</span> : null}
                  <span className="italic">{esp}</span>
                </span>
                {dictamen ? (
                  <span className="text-[10px] text-muted-foreground font-mono">
                    Dictamen: {dictamen}
                  </span>
                ) : null}
              </li>
            );
          })}
        </ul>
      </TooltipContent>
    </Tooltip>
  );
}
