"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Percent,
  Banknote,
  ShieldAlert,
  CircleCheck,
  CircleDot,
  Lock,
} from "lucide-react";
import type { RevisionesVigentesTableProps } from "../types/liquidacion-edificaciones-form.types";

/** Format a decimal ratio as percentage: 0.18 -> "18.00%" */
const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(2)}%`;
};

/** Format a number as Peruvian soles: 500 -> "S/ 500.00" */
const formatSoles = (value: number): string => {
  return `S/ ${value.toFixed(2)}`;
};

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
        <div className="space-y-1">
          <div className="h-3 w-12 bg-muted rounded" />
          <div className="h-4 w-16 bg-muted rounded" />
        </div>
        <div className="space-y-1">
          <div className="h-3 w-16 bg-muted rounded" />
          <div className="h-4 w-20 bg-muted rounded" />
        </div>
        <div className="space-y-1">
          <div className="h-3 w-16 bg-muted rounded" />
          <div className="h-4 w-20 bg-muted rounded" />
        </div>
        <div className="space-y-1">
          <div className="h-3 w-20 bg-muted rounded" />
          <div className="h-4 w-16 bg-muted rounded" />
        </div>
      </div>
    </div>
  );
}

export function RevisionesVigentesTable({
  revisiones,
  selectedIds,
  onToggleRevision,
  isLoading,
  lockedIds = [],
}: RevisionesVigentesTableProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
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
    <div className="flex flex-col gap-3">
      {revisiones.map((rev) => {
        const isSelected = selectedIds.includes(rev.id);
        const isDisabled = !rev.habilitada;
        const isLocked = lockedIds.includes(rev.id);

        return (
          <div
            key={rev.id}
            className={[
              "rounded-xl border bg-card p-4 space-y-3 transition-all duration-200",
              isSelected
                ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                : "border-border hover:border-primary/40",
              isDisabled && "opacity-50",
              isLocked && !isDisabled && "border-amber-400/50 bg-amber-50/30",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {/* Header row: icon badge + name + status badge + checkbox */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                {/* Icon badge */}
                <div
                  className={[
                    "flex items-center justify-center rounded-lg border shrink-0",
                    isLocked && !isDisabled
                      ? "bg-amber-100 text-amber-600 border-amber-300"
                      : isSelected
                        ? "bg-primary text-primary-foreground border-primary"
                        : isDisabled
                          ? "bg-muted text-muted-foreground border-border"
                          : "bg-primary/10 text-primary border-primary/20",
                  ].join(" ")}
                >
                  {isLocked && !isDisabled ? (
                    <Lock className="h-4 w-4" />
                  ) : isDisabled ? (
                    <ShieldAlert className="h-4 w-4" />
                  ) : isSelected ? (
                    <CircleCheck className="h-4 w-4" />
                  ) : (
                    <CircleDot className="h-4 w-4" />
                  )}
                </div>

                {/* Name and status */}
                <div className="flex flex-col gap-0.5 min-w-0">
                  <div className="flex flex-wrap gap-1">
                    {rev.especialidades.length > 0 ? (
                      rev.especialidades.map((e) => (
                        <Badge key={e.id} variant="secondary" className="text-xs">
                          {e.nombre}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-xs text-muted-foreground">Sin especialidades</span>
                    )}
                  </div>
                  {isLocked && !isDisabled ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-600 uppercase tracking-wide">
                      <Lock className="h-3 w-3" />
                      Obligatoria
                    </span>
                  ) : isDisabled ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                      <ShieldAlert className="h-3 w-3" />
                      Inhabilitada
                    </span>
                  ) : isSelected ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-primary uppercase tracking-wide">
                      <CircleCheck className="h-3 w-3" />
                      Seleccionada
                    </span>
                  ) : (
                    <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                      Disponible
                    </span>
                  )}
                </div>
              </div>

              <Checkbox
                checked={isSelected}
                onCheckedChange={() => !isLocked && !isDisabled && onToggleRevision(rev.id)}
                disabled={isDisabled || isLocked}
                className="shrink-0 mt-0.5"
                aria-label={
                  rev.especialidades.length > 0
                    ? rev.especialidades.length === 1
                      ? `Seleccionar ${rev.especialidades[0].nombre}`
                      : `Seleccionar ${rev.especialidades[0].nombre} y ${rev.especialidades.length - 1} más`
                    : "Seleccionar"
                }
              />
            </div>

            {/* Numeric fields grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 text-xs pl-[44px]">
              {/* % Liq. */}
              <div className="flex items-center gap-1.5">
                <Percent className="h-3.5 w-3.5 text-primary/60 shrink-0" />
                <div className="space-y-0.5 min-w-0">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                    % Liq.
                  </span>
                  <p className="font-medium text-foreground truncate">
                    {formatPercent(rev.porcentaje_liquidacion)}
                  </p>
                </div>
              </div>

              {/* Derecho Mín. */}
              <div className="flex items-center gap-1.5">
                <Banknote className="h-3.5 w-3.5 text-primary/60 shrink-0" />
                <div className="space-y-0.5 min-w-0">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                    Derecho Mín.
                  </span>
                  <p className="font-medium text-foreground truncate">
                    {formatSoles(rev.derecho_minimo)}
                  </p>
                </div>
              </div>

              {/* Derecho Máx. */}
              <div className="flex items-center gap-1.5">
                <Banknote className="h-3.5 w-3.5 text-primary/60 shrink-0" />
                <div className="space-y-0.5 min-w-0">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                    Derecho Máx.
                  </span>
                  <p className="font-medium text-foreground truncate">
                    {rev.derecho_maximo != null
                      ? formatSoles(rev.derecho_maximo)
                      : "—"}
                  </p>
                </div>
              </div>

              {/* % Mín. UIT */}
              <div className="flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5 text-primary/60 shrink-0" />
                <div className="space-y-0.5 min-w-0">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                    % Mín. UIT
                  </span>
                  <p className="font-medium text-foreground truncate">
                    {formatPercent(rev.porcentaje_minimo_uit)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}