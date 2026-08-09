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
    <div className="grid grid-auto-fill-sm gap-4">
      {revisiones.map((rev) => {
        const isSelected = selectedId === rev.id;
        const isDisabled = !rev.habilitada;

        return (
          <button
            key={rev.id}
            type="button"
            disabled={isDisabled}
            onClick={() => !isDisabled && onSelectRevision(rev.id)}
            className={[
              "rounded-xl border bg-card p-4 transition-all duration-200 text-left w-full flex flex-col gap-3",
              isSelected
                ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                : "border-border hover:border-primary/40 cursor-pointer",
              isDisabled && "opacity-50 cursor-not-allowed",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            {/* Header: icono + especialidades + estado */}
            <div className="flex items-start gap-3">
              {/* Indicador de estado */}
              <div
                className={[
                  "flex items-center justify-center rounded-lg border shrink-0 p-1.5",
                  isSelected
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-muted text-muted-foreground border-border",
                  isDisabled && "bg-muted/50 text-muted-foreground/50",
                ].join(" ")}
              >
                {isDisabled ? (
                  <ShieldAlert className="h-4 w-4" />
                ) : isSelected ? (
                  <CircleCheck className="h-4 w-4" />
                ) : (
                  <Star className="h-4 w-4" />
                )}
              </div>

              {/* Especialidades + estado label */}
              <div className="flex-1 min-w-0 space-y-1.5">
                {/* Especialidades como badges */}
                <div className="flex flex-wrap gap-1.5">
                  {rev.especialidades.length > 0 ? (
                    rev.especialidades.map((e) => (
                      <Badge
                        key={e.id}
                        variant={isSelected ? "default" : "secondary"}
                        className="text-xs font-medium px-2 py-0.5"
                      >
                        {e.nombre}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      Sin especialidades
                    </span>
                  )}
                </div>
                {/* Estado */}
                {isDisabled ? (
                  <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                    <ShieldAlert className="h-3 w-3" />
                    Inhabilitada
                  </span>
                ) : isSelected ? (
                  <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-primary uppercase tracking-wide">
                    <CircleCheck className="h-3 w-3" />
                    Seleccionada
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-secondary-foreground uppercase tracking-wide">
                    <Star className="h-3 w-3" />
                    Disponible
                  </span>
                )}
              </div>
            </div>

            {/* Métricas en grid 2x2 */}
            <div className="grid grid-cols-2 gap-2.5 text-xs pl-[46px]">
              <div className="flex items-start gap-1.5">
                <Percent className="h-3.5 w-3.5 text-primary/60 shrink-0 mt-0.5" />
                <div className="space-y-0.5 min-w-0">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                    Liq.
                  </span>
                  <p className="font-medium text-foreground truncate">
                    {formatPercent(rev.porcentaje_liquidacion)}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-1.5">
                <Banknote className="h-3.5 w-3.5 text-primary/60 shrink-0 mt-0.5" />
                <div className="space-y-0.5 min-w-0">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                    Der. Mín.
                  </span>
                  <p className="font-medium text-foreground truncate">
                    {formatSoles(rev.derecho_minimo)}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-1.5">
                <Coins className="h-3.5 w-3.5 text-primary/60 shrink-0 mt-0.5" />
                <div className="space-y-0.5 min-w-0">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide">
                    Der. Máx.
                  </span>
                  <p className="font-medium text-foreground truncate">
                    {rev.derecho_maximo != null
                      ? formatSoles(rev.derecho_maximo)
                      : "—"}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-1.5">
                <FileText className="h-3.5 w-3.5 text-primary/60 shrink-0 mt-0.5" />
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
          </button>
        );
      })}
    </div>
  );
}
