"use client";

import { Calendar, ChevronDown, FileText } from "lucide-react";
import { CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import {
  formatCurrency,
  formatDate,
  getEstadoBadgeClass,
} from "./cards/../liquidacion-ui";

export interface LiquidacionCardHeaderData {
  public_id: string;
  estado?: string;
  fecha_registro: string;
  proyectoNombre: string;
  kindBadge: string;
  expediente?: string | null;
  total?: number;
}

interface LiquidacionCardHeaderProps {
  data: LiquidacionCardHeaderData;
  rightSlotChildren?: React.ReactNode;
  /**
   * Optional display-only version of public_id.
   * When provided, this is shown in the UI instead of public_id.
   * Does not affect rightSlotChildren or other logic — only visual display.
   * Use this to strip prefixes (e.g., "LIQ-") from the display without
   * changing backend data.
   */
  displayPublicId?: string;
}

export function LiquidacionCardHeader({
  data,
  rightSlotChildren,
  displayPublicId,
}: LiquidacionCardHeaderProps) {
  const {
    public_id,
    estado,
    fecha_registro,
    proyectoNombre,
    kindBadge,
    expediente,
    total,
  } = data;

  return (
    <CollapsibleTrigger className="w-full px-5 py-4 bg-gradient-to-r from-muted/40 via-muted/20 to-transparent border-b border-border/60 text-left hover:bg-muted/30 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50">
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 group-hover:bg-primary/15 transition-colors">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-lg font-black text-foreground tracking-tight">
                {displayPublicId ?? public_id}
              </h3>
              <span
                className={cn(
                  "shrink-0 inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                  getEstadoBadgeClass(estado ?? ""),
                )}
              >
                {estado}
              </span>
            </div>

            <div className="flex items-center gap-3 mt-1 flex-wrap">
              {proyectoNombre && (
                <>
                  <span className="text-xs text-muted-foreground truncate max-w-[280px]">
                    {proyectoNombre}
                  </span>
                  <span className="text-xs text-muted-foreground/60 hidden sm:inline">
                    •
                  </span>
                </>
              )}
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-xs font-semibold text-secondary-foreground-foreground">
                {kindBadge}
              </span>
              {expediente && (
                <span className="text-xs text-muted-foreground font-mono hidden md:inline">
                  Exp: {expediente}
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground/70">
              <div className="flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" />
                <span>{formatDate(fecha_registro)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2 lg:items-end">
          <div className="bg-primary/5 border border-primary/10 rounded-xl px-4 py-2.5 flex items-center gap-3">
            {total != null && (
              <div className="text-right">
                <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
                  Total a Pagar
                </p>
                <p className="text-xl font-black text-primary tracking-tight">
                  {formatCurrency(total)}
                </p>
              </div>
            )}
            <ChevronDown className="h-4 w-4 text-primary/40 group-data-[state=open]:rotate-180 transition-transform" />
          </div>
          {rightSlotChildren}
        </div>
      </div>
    </CollapsibleTrigger>
  );
}
