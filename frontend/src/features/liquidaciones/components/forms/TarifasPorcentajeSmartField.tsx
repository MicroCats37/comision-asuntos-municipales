"use client";

import { CheckSquare, Percent, Square } from "lucide-react";
/**
 * TarifasPorcentajeSmartField — Smart Field for PorcentajeObra tariff selection.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<EdificacionesFormData>` from parent
 * - Fetches vigentes via useTarifasVigentesPorcentaje (GET /liquidaciones/{tipo}/tarifas/vigentes)
 * - NEW contract: returns { tarifas: [tarifa_unica], especialidades_disponibles: [...] }
 * - Shows ONE read-only card with the single tariff percentage
 * - Shows checkboxes for especialidades_disponibles (user selects which apply)
 * - On toggle: setValue("especialidades_seleccionadas", [...]) and setValue("tarifa_unica_id", id)
 * - OWN state for selected specialty IDs. Does NOT cause form re-render.
 */
import { useCallback } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useTarifasVigentesPorcentaje } from "../../hooks/useTarifasVigentes";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface TarifasPorcentajeSmartFieldProps {
  methods: UseFormReturn<any>;
  /** Tipo de liquidación para el endpoint (default: edificaciones) */
  tipo?: string;
}

const formatPercent = (value: number): string => `${(value * 100).toFixed(4)}%`;

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
      <div className="h-4 w-24 bg-muted rounded" />
    </div>
  );
}

export function TarifasPorcentajeSmartField({
  methods,
  tipo = "edificaciones",
}: TarifasPorcentajeSmartFieldProps) {
  // Source of truth = form field, so parent auto-select-all syncs the visual
  const selectedEspecialidades =
    methods.watch("especialidades_seleccionadas") ?? [];

  const { data, isLoading } = useTarifasVigentesPorcentaje(tipo);

  const tarifas = data?.tarifas ?? [];
  const especialidades = data?.especialidades_disponibles ?? [];
  const tarifaUnica = tarifas[0];

  const handleToggleEspecialidad = useCallback(
    (id: string) => {
      const next = selectedEspecialidades.includes(id)
        ? selectedEspecialidades.filter((x: string) => x !== id)
        : [...selectedEspecialidades, id];
      methods.setValue("especialidades_seleccionadas", next, {
        shouldValidate: true,
      });
    },
    [methods, selectedEspecialidades],
  );

  const handleSelectAll = useCallback(() => {
    const allIds = especialidades.map((e) => e.id);
    methods.setValue("especialidades_seleccionadas", allIds, {
      shouldValidate: true,
    });
  }, [especialidades, methods]);

  if (isLoading) {
    return (
      <div className="space-y-2">
        <label className="text-sm font-medium">Tarifas Vigentes</label>
        <div className="flex flex-col md:flex-row md:flex-wrap gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <LoadingCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (!tarifaUnica) {
    return (
      <div className="space-y-2">
        <label className="text-sm font-medium">Tarifas Vigentes</label>
        <p className="text-sm text-muted-foreground text-center py-4">
          No hay tarifas vigentes disponibles
        </p>
      </div>
    );
  }

  // Set tarifa_unica_id once the tariff is known
  methods.setValue("tarifa_unica_id", tarifaUnica.id, {
    shouldValidate: false,
  });

  // Total aplicado = tarifa única x cantidad de especialidades seleccionadas
  const totalAplicado =
    selectedEspecialidades.length > 0
      ? tarifaUnica.porcentaje_liquidacion * selectedEspecialidades.length
      : tarifaUnica.porcentaje_liquidacion;

  const error = methods.formState.errors.especialidades_seleccionadas;

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium">Tarifa Única</label>

      {/* ── Single tariff card (read-only) ── */}
      <div
        className={[
          "rounded-xl border bg-card px-4 py-3 w-full flex items-center justify-between",
          "border-primary/30 bg-primary/[0.03]",
        ].join(" ")}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center rounded-lg border border-primary/20 bg-primary/10 p-2">
            <Percent className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">
              Porcentaje de Obra
            </p>
            <p className="text-xs text-muted-foreground">
              Tarifa única por período
            </p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-lg font-bold text-primary">
            {formatPercent(totalAplicado)}
          </span>
          {selectedEspecialidades.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {formatPercent(tarifaUnica.porcentaje_liquidacion)} ×{" "}
              {selectedEspecialidades.length} especialidades
            </p>
          )}
        </div>
      </div>

      {/* ── Specialty selector ── */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">
            Especialidades a aplicar
            {selectedEspecialidades.length > 0 && (
              <span className="ml-2 text-xs text-muted-foreground">
                ({selectedEspecialidades.length} seleccionadas)
              </span>
            )}
          </label>
          <button
            type="button"
            onClick={handleSelectAll}
            className="text-xs text-primary hover:underline"
          >
            Seleccionar todas
          </button>
        </div>
        {error && (
          <p className="text-xs text-destructive">
            {error.message?.toString()}
          </p>
        )}
        <div className="flex flex-col md:flex-row md:flex-wrap gap-2">
          {especialidades.map((esp) => {
            const isSelected = selectedEspecialidades.includes(esp.id);
            return (
              <button
                key={esp.id}
                type="button"
                onClick={() => handleToggleEspecialidad(esp.id)}
                className={[
                  "rounded-lg border bg-card px-3 py-2 transition-all duration-200 text-left w-full md:flex-1 md:min-w-[180px] flex items-center gap-2 cursor-pointer",
                  isSelected
                    ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                    : "border-border hover:border-primary/40",
                ].join(" ")}
              >
                {isSelected ? (
                  <CheckSquare className="h-4 w-4 text-primary shrink-0" />
                ) : (
                  <Square className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
                <span className="text-sm font-medium truncate">
                  {esp.nombre}
                </span>
                <span className="text-xs text-muted-foreground shrink-0">
                  ({esp.codigo})
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
