"use client";

/**
 * HabilitacionUrbanaTarifaSelector — Compact tariff selector for HU.
 *
 * Shows HU-specific fields:
 * - costo_por_m2
 * - area_m2
 * - derecho_minimo / derecho_maximo
 *
 * Auto-selects single enabled tariff — caller hides this component when only
 * one enabled tariff exists.
 */
import { Tag } from "lucide-react";
import type { TarifaVigenteHabilitacionUrbana } from "../types/liquidacion-habilitacion-urbana.types";

interface HabilitacionUrbanaTarifaSelectorProps {
  tarifas: TarifaVigenteHabilitacionUrbana[];
  selectedTarifaId: string | null;
  onSelectTarifa: (tarifaId: string) => void;
  isLoading: boolean;
}

function formatSoles(value: number): string {
  return `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
}

export function HabilitacionUrbanaTarifaSelector({
  tarifas,
  selectedTarifaId,
  onSelectTarifa,
  isLoading,
}: HabilitacionUrbanaTarifaSelectorProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 min-w-0">
        <label className="text-primary font-semibold text-sm flex items-center gap-1">
          <Tag className="h-3.5 w-3.5" />
          Tarifa
          <span className="text-destructive">*</span>
        </label>
        <div className="rounded-xl border border-border bg-card p-4 animate-pulse space-y-3">
          <div className="h-4 w-40 bg-muted rounded" />
          <div className="grid grid-cols-2 gap-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-12 bg-muted rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 min-w-0">
      <label className="text-primary font-semibold text-sm flex items-center gap-1">
        <Tag className="h-3.5 w-3.5" />
        Tarifa
        <span className="text-destructive">*</span>
      </label>
      {tarifas.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No hay tarifas vigentes disponibles
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {tarifas.map((tarifa) => {
            const isSelected = selectedTarifaId === tarifa.tarifa_id;
            const isDisabled = !tarifa.habilitada;
            return (
              <button
                key={tarifa.tarifa_id}
                type="button"
                disabled={isDisabled}
                onClick={() => !isDisabled && onSelectTarifa(tarifa.tarifa_id)}
                className={[
                  "rounded-xl border bg-card p-3 transition-all duration-200 text-left w-full flex flex-col gap-2",
                  isSelected
                    ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                    : "border-border hover:border-primary/40",
                  isDisabled && "opacity-50 cursor-not-allowed",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <span className="text-xs font-semibold text-foreground truncate">
                      {tarifa.costo_por_m2 != null
                        ? `${formatSoles(tarifa.costo_por_m2)}/m²`
                        : "—"}
                    </span>
                    {tarifa.area_m2 != null && (
                      <span className="text-[10px] text-muted-foreground">
                        Base: {tarifa.area_m2} m²
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col gap-0.5 items-end shrink-0">
                    <span className="text-[10px] text-muted-foreground">
                      Der. mín:
                    </span>
                    <span className="text-xs font-semibold text-foreground">
                      {formatSoles(tarifa.derecho_minimo)}
                    </span>
                  </div>
                </div>
                {tarifa.derecho_maximo != null && (
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">
                      Der. máx:
                    </span>
                    <span className="text-xs font-medium text-foreground">
                      {formatSoles(tarifa.derecho_maximo)}
                    </span>
                  </div>
                )}
                {isSelected && (
                  <div className="text-[10px] font-semibold text-primary pt-1 border-t border-primary/20">
                    ✓ Seleccionada
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
