"use client";

import {
  Banknote,
  CircleCheck,
  Coins,
  FileText,
  Percent,
  ShieldAlert,
  Star,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { RevisionesVigentesTableProps } from "../types/liquidacion-edificaciones-form.types";

const formatPercent = (value: number): string => `${(value * 100).toFixed(2)}%`;
const formatSoles = (value: number): string => `S/ ${value.toFixed(2)}`;

function LoadingCard() {
  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3 animate-pulse">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="h-9 w-9 bg-muted rounded-lg" />
          <div className="h-4 w-40 bg-muted rounded" />
        </div>
        <div className="h-4 w-4 bg-muted rounded" />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-1">
            <div className="h-3 w-12 bg-muted rounded" />
            <div className="h-4 w-16 bg-muted rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function RevisionesVigentesTable({
  revisiones,
  selectedId,
  onSelectRevision,
  isLoading,
  lockedIds = [],
}: RevisionesVigentesTableProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col md:flex-row md:flex-wrap gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <LoadingCard key={i} />
        ))}
      </div>
    );
  }

  if (revisiones.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-4">
        No hay especialidades/revisiones vigentes disponibles
      </p>
    );
  }

  return (
    <div className="flex flex-col md:flex-row md:flex-wrap gap-2">
      {revisiones.map((rev) => {
        const isSelected = selectedId === rev.id;
        const isUnavailable = !rev.habilitada;
        const isLocked = lockedIds.includes(rev.id);
        const isDisabled = isUnavailable || isLocked;

        return (
          <button
            key={rev.id}
            type="button"
            disabled={isDisabled}
            onClick={() => !isDisabled && onSelectRevision(rev.id)}
            className={[
              "rounded-lg border bg-card px-3 py-2 transition-all duration-200 text-left w-full md:flex-1 md:min-w-[280px] flex flex-col gap-2",
              isSelected
                ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                : "border-border hover:border-primary/40 cursor-pointer",
              isUnavailable && "opacity-50 cursor-not-allowed",
              isLocked && !isUnavailable && "cursor-default",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {/* Especialidades */}
            <div className="flex items-start gap-2 min-w-0">
              {/* Indicador de estado */}
              <div
                className={[
                  "flex items-center justify-center rounded-md border shrink-0 p-1 mt-0.5",
                  isSelected
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-muted text-muted-foreground border-border",
                  isDisabled && "bg-muted/50 text-muted-foreground/50",
                ].join(" ")}
              >
                {isUnavailable ? (
                  <ShieldAlert className="h-3.5 w-3.5" />
                ) : isSelected ? (
                  <CircleCheck className="h-3.5 w-3.5" />
                ) : (
                  <Star className="h-3.5 w-3.5" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap gap-1.5">
                  {rev.especialidades.length > 0 ? (
                    rev.especialidades.map((e) => (
                      <Badge
                        key={e.id}
                        variant={isSelected ? "default" : "secondary"}
                        className="text-[10px] font-medium px-1.5 py-0.5"
                        >
                          {e.nombre}
                        </Badge>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground">Sin especialidades</span>
                  )}
                </div>
              </div>
            </div>

            {/* Métricas compactas */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground border-t border-border/40 pt-2">
              <div className="inline-flex items-center gap-1.5">
                <Percent className="h-3 w-3 text-primary/60 shrink-0" />
                <span>Liq.</span>
                <span className="font-medium text-foreground">{formatPercent(rev.porcentaje_liquidacion)}</span>
              </div>
              <div className="inline-flex items-center gap-1.5">
                <Banknote className="h-3 w-3 text-primary/60 shrink-0" />
                <span>Der. mín.</span>
                <span className="font-medium text-foreground">{formatSoles(rev.derecho_minimo)}</span>
              </div>
              <div className="inline-flex items-center gap-1.5">
                <Coins className="h-3 w-3 text-primary/60 shrink-0" />
                <span>Der. máx.</span>
                <span className="font-medium text-foreground">
                  {rev.derecho_maximo != null ? formatSoles(rev.derecho_maximo) : "—"}
                </span>
              </div>
              <div className="inline-flex items-center gap-1.5">
                <FileText className="h-3 w-3 text-primary/60 shrink-0" />
                <span>% mín. UIT</span>
                <span className="font-medium text-foreground">{formatPercent(rev.porcentaje_minimo_uit)}</span>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
