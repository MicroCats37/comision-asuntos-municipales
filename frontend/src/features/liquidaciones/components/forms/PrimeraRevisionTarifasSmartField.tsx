"use client";

/**
 * PrimeraRevisionTarifasSmartField — Smart Field visual para primera revisión
 * de liquidaciones PorcentajeObra (Edificaciones, Taludes, Impacto Vial).
 *
 * Comportamiento:
 * - Carga todas las tarifas vigentes del motor PorcentajeObra
 * - AUTO-SELECCIONA todas al montar (el backend acepta "todo o nada":
 *   si se envía vacío, auto-rellena con todas — seleccionar todas equivale)
 * - UI READ-ONLY: muestra un summary card con la suma de especialidades,
 *   NO hay opción de seleccionar/deseleccionar
 *
 * Arquitectura:
 * - Receives `methods: UseFormReturn<any>` desde el form
 * - Sync al form via `methods.setValue` (todas seleccionadas, sin interacción)
 */
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import type { UseFormReturn } from "react-hook-form";
import { Percent, CheckCircle2, Layers } from "lucide-react";
import api from "@/lib/api";

/** Backend real: GET /liquidaciones/{tipo}/tarifas/vigentes → data.tarifas[] */
interface TarifaVigente {
  id: string;
  especialidad: string;
  porcentaje_liquidacion: number;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface PrimeraRevisionTarifasSmartFieldProps {
  methods: UseFormReturn<any>;
  /** Tipo de liquidación para el endpoint (default: edificaciones) */
  tipo?: string;
}

const formatPercent = (value: number): string => `${(value * 100).toFixed(2)}%`;

export function PrimeraRevisionTarifasSmartField({
  methods,
  tipo = "edificaciones",
}: PrimeraRevisionTarifasSmartFieldProps) {
  const { data: tarifas, isLoading } = useQuery<TarifaVigente[]>({
    queryKey: ["liquidaciones", tipo, "tarifas-vigentes"],
    queryFn: async () => {
      const { data } = await api.get(`/liquidaciones/${tipo}/tarifas/vigentes`);
      return data.data?.tarifas || [];
    },
  });

  // Auto-select ALL on first load (read-only — all are applied)
  useEffect(() => {
    if (tarifas && tarifas.length > 0) {
      const allIds = tarifas.map((t) => t.id);
      methods.setValue("tarifas_ids", allIds, { shouldValidate: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tarifas]);

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

  if (!tarifas || tarifas.length === 0) {
    return (
      <div className="space-y-2 rounded-xl border border-border/50 bg-card p-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">Tarifas Vigentes</h3>
        </div>
        <p className="text-sm text-muted-foreground text-center py-3">
          No hay tarifas vigentes disponibles
        </p>
      </div>
    );
  }

  const totalPorcentaje = tarifas.reduce(
    (acc, t) => acc + Number(t.porcentaje_liquidacion),
    0,
  );

  return (
    <div className="space-y-3 rounded-xl border border-primary/20 bg-primary/[0.03] p-4">
      <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-2">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">Tarifas Vigentes</h3>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-0.5 text-xs font-bold text-primary">
          <Percent className="h-3 w-3" />
          {formatPercent(totalPorcentaje)} total
        </span>
      </div>

      {/* Summary: todas las especialidades aplicadas */}
      <div className="flex flex-wrap gap-1.5">
        {tarifas.map((tarifa) => (
          <span
            key={tarifa.id}
            className="inline-flex items-center gap-1 rounded-md border border-primary/20 bg-background px-2 py-1 text-xs font-medium"
          >
            <Layers className="h-3 w-3 text-primary/60" />
            {tarifa.especialidad}
            <span className="text-muted-foreground">·</span>
            <span className="font-bold">{formatPercent(tarifa.porcentaje_liquidacion)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
