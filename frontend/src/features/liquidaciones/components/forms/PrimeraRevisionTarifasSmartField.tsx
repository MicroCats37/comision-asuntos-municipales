"use client";

import { CheckCircle2, Layers, Percent } from "lucide-react";
/**
 * PrimeraRevisionTarifasSmartField — Smart Field visual para primera revisión
 * de liquidaciones PorcentajeObra (Edificaciones, Taludes, Impacto Vial).
 *
 * NEW contract:
 * - GET /liquidaciones/{tipo}/tarifas/vigentes → { tarifas: [tarifa_unica], especialidades_disponibles: [...] }
 *   (via useTarifasVigentesPorcentaje)
 * - Shows ONE read-only card with the single tariff percentage
 * - Shows all especialidades as applied chips (all selected by default)
 * - Sets tarifa_unica_id + especialidades_seleccionadas in the form via setValue
 *
 * Arquitectura:
 * - Receives `methods: UseFormReturn<any>` desde el form
 * - Sync al form via `methods.setValue` (todas seleccionadas, sin interacción)
 */
import { useEffect } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useTarifasVigentesPorcentaje } from "../../hooks/useTarifasVigentes";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface PrimeraRevisionTarifasSmartFieldProps {
  methods: UseFormReturn<any>;
  /** Tipo de liquidación para el endpoint (default: edificaciones) */
  tipo?: string;
}

const formatPercent = (value: number): string => `${(value * 100).toFixed(4)}%`;

export function PrimeraRevisionTarifasSmartField({
  methods,
  tipo = "edificaciones",
}: PrimeraRevisionTarifasSmartFieldProps) {
  const { data, isLoading } = useTarifasVigentesPorcentaje(tipo);

  const tarifas = data?.tarifas ?? [];
  const especialidades = data?.especialidades_disponibles ?? [];
  const tarifaUnica = tarifas[0];

  // Total aplicado = tarifa única x todas las especialidades seleccionadas
  const totalAplicado =
    especialidades.length > 0
      ? tarifaUnica.porcentaje_liquidacion * especialidades.length
      : (tarifaUnica?.porcentaje_liquidacion ?? 0);

  // Auto-select ALL on first load and set tarifa_unica_id
  useEffect(() => {
    if (tarifaUnica) {
      methods.setValue("tarifa_unica_id", tarifaUnica.id, {
        shouldValidate: false,
      });
    }
    if (especialidades.length > 0) {
      const allIds = especialidades.map((e) => e.id);
      methods.setValue("especialidades_seleccionadas", allIds, {
        shouldValidate: true,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tarifaUnica, especialidades]);

  if (isLoading) {
    return (
      <div className="space-y-3 rounded-xl border border-border/50 bg-card p-4 animate-pulse">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <div className="h-4 w-32 bg-muted rounded" />
        </div>
        <div className="h-4 w-48 bg-muted rounded" />
        <div className="h-4 w-40 bg-muted rounded" />
      </div>
    );
  }

  if (!tarifaUnica) {
    return (
      <div className="space-y-2 rounded-xl border border-border/50 bg-card p-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            Tarifas Vigentes
          </h3>
        </div>
        <p className="text-sm text-muted-foreground text-center py-3">
          No hay tarifas vigentes disponibles
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-xl border border-primary/20 bg-primary/[0.03] p-4">
      <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-2">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            Tarifa Única
          </h3>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-0.5 text-xs font-bold text-primary">
          <Percent className="h-3 w-3" />
          {formatPercent(totalAplicado)}
          <span className="font-normal text-primary/70">
            × {especialidades.length} esp.
          </span>
        </span>
      </div>

      {/* Summary: all applied specialties */}
      <div className="flex flex-wrap gap-1.5">
        {especialidades.map((esp) => (
          <span
            key={esp.id}
            className="inline-flex items-center gap-1 rounded-md border border-primary/20 bg-background px-2 py-1 text-xs font-medium"
          >
            <Layers className="h-3 w-3 text-primary/60" />
            {esp.nombre}
            <span className="text-muted-foreground">·</span>
            <span className="font-bold text-primary">{esp.codigo}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
