"use client";

/**
 * TarifasPorcentajeSmartField — Smart Field for PorcentajeObra tariff selection.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<EdificacionesFormData>` from parent
 * - Fetches vigentes from GET /liquidaciones/edificaciones/tarifas/vigentes
 * - Shows list of especialidades with porcentaje, checkboxes to select
 * - On selection change: `methods.setValue("tarifas_ids", selectedIds)`
 * - OWN state for selected IDs. Does NOT cause form re-render.
 */
import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import type { UseFormReturn } from "react-hook-form";
import { Percent, CircleCheck, Star } from "lucide-react";
import api from "@/lib/api";

/** Backend real: { id, especialidad: string, porcentaje_liquidacion: float } */
interface TarifaVigente {
  id: string;
  especialidad: string;
  porcentaje_liquidacion: number;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface TarifasPorcentajeSmartFieldProps {
  methods: UseFormReturn<any>;
}

const formatPercent = (value: number): string => `${(value * 100).toFixed(2)}%`;

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
}: TarifasPorcentajeSmartFieldProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const { data: tarifas, isLoading } = useQuery<TarifaVigente[]>({
    queryKey: ["liquidaciones", "edificaciones", "tarifas-vigentes"],
    queryFn: async () => {
      const { data } = await api.get("/liquidaciones/edificaciones/tarifas/vigentes");
      return data.data?.tarifas || [];
    },
  });

  const handleToggle = useCallback(
    (id: string) => {
      setSelectedIds((prev) => {
        const next = prev.includes(id)
          ? prev.filter((x) => x !== id)
          : [...prev, id];
        methods.setValue("tarifas_ids", next, { shouldValidate: true });
        return next;
      });
    },
    [methods],
  );

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

  if (!tarifas || tarifas.length === 0) {
    return (
      <div className="space-y-2">
        <label className="text-sm font-medium">Tarifas Vigentes</label>
        <p className="text-sm text-muted-foreground text-center py-4">
          No hay tarifas vigentes disponibles
        </p>
      </div>
    );
  }

  const error = methods.formState.errors.tarifas_ids;

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">
        Tarifas Vigentes
        {selectedIds.length > 0 && (
          <span className="ml-2 text-xs text-muted-foreground">
            ({selectedIds.length} seleccionadas)
          </span>
        )}
      </label>
      {error && (
        <p className="text-xs text-destructive">{error.message?.toString()}</p>
      )}
      <div className="flex flex-col md:flex-row md:flex-wrap gap-2">
        {tarifas.map((tarifa) => {
          const isSelected = selectedIds.includes(tarifa.id);

          return (
            <button
              key={tarifa.id}
              type="button"
              onClick={() => handleToggle(tarifa.id)}
              className={[
                "rounded-lg border bg-card px-3 py-2 transition-all duration-200 text-left w-full md:flex-1 md:min-w-[220px] flex flex-col gap-1.5 cursor-pointer",
                isSelected
                  ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                  : "border-border hover:border-primary/40",
              ].join(" ")}
            >
              <div className="flex items-center gap-2">
                <div
                  className={[
                    "flex items-center justify-center rounded-md border shrink-0 p-1",
                    isSelected
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-muted text-muted-foreground border-border",
                  ].join(" ")}
                >
                  {isSelected ? (
                    <CircleCheck className="h-3.5 w-3.5" />
                  ) : (
                    <Star className="h-3.5 w-3.5" />
                  )}
                </div>
                <span className="text-sm font-medium truncate">
                  {tarifa.especialidad}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground pl-8">
                <Percent className="h-3 w-3 text-primary/60" />
                <span>{formatPercent(tarifa.porcentaje_liquidacion)}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
