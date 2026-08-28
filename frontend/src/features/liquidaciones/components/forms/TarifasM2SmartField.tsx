"use client";

import { Banknote, CircleCheck, MapPin, Square } from "lucide-react";
/**
 * TarifasM2SmartField — Smart Field para selección de tarifa M2 (HU, MS).
 *
 * Backend GET /liquidaciones/{tipo}/tarifas/vigentes devuelve:
 * {
 *   tarifa_vigente: { datos: { id, costo_por_m2 } },
 *   derecho_vigente: { datos: { id, derecho_minimo, derecho_maximo } }
 * }
 * Single select — setValue("tarifa_m2_id", id)
 */
import { useEffect, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useTarifasVigentesM2 } from "../../hooks/useTarifasVigentes";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface TarifasM2SmartFieldProps {
  methods: UseFormReturn<any>;
  tipo?: "habilitacion-urbana" | "mecanica-suelos";
}

const formatSoles = (value: number | undefined): string =>
  value == null ? "—" : `S/ ${Number(value).toFixed(2)}`;

export function TarifasM2SmartField({
  methods,
  tipo = "habilitacion-urbana",
}: TarifasM2SmartFieldProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useTarifasVigentesM2(tipo);

  const tarifa = data?.tarifa_vigente?.datos;
  const derecho = data?.derecho_vigente?.datos;

  // Auto-select the single tariff on load
  useEffect(() => {
    if (tarifa?.id && !selectedId) {
      setSelectedId(tarifa.id);
      methods.setValue("tarifa_m2_id", tarifa.id, { shouldValidate: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tarifa?.id]);
  if (isLoading) {
    return (
      <div className="space-y-2">
        <label className="text-sm font-medium">Tarifa Vigente</label>
        <div className="rounded-xl border border-border bg-card p-4 space-y-3 animate-pulse">
          <div className="h-4 w-40 bg-muted rounded" />
          <div className="h-4 w-24 bg-muted rounded" />
        </div>
      </div>
    );
  }

  if (!tarifa?.id) {
    return (
      <div className="space-y-2">
        <label className="text-sm font-medium">Tarifa Vigente</label>
        <p className="text-sm text-muted-foreground text-center py-4">
          No hay tarifa M2 vigente disponible
        </p>
      </div>
    );
  }

  const isSelected = selectedId === tarifa.id;

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">
        Tarifa Vigente
        {isSelected && (
          <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[10px] font-bold text-primary">
            <CircleCheck className="h-3 w-3" />
            Seleccionada
          </span>
        )}
      </label>
      <button
        type="button"
        onClick={() => {
          const next = isSelected ? null : (tarifa.id ?? null);
          setSelectedId(next);
          methods.setValue("tarifa_m2_id", next ?? undefined, {
            shouldValidate: true,
          });
        }}
        className={[
          "rounded-lg border bg-card px-3 py-2 transition-all duration-200 text-left w-full flex flex-col gap-2 cursor-pointer",
          isSelected
            ? "border-primary ring-1 ring-primary/30 bg-primary/5"
            : "border-border hover:border-primary/40",
        ].join(" ")}
      >
        <div className="flex items-start gap-2 min-w-0">
          <div
            className={[
              "flex items-center justify-center rounded-md border shrink-0 p-1 mt-0.5",
              isSelected
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-muted text-muted-foreground border-border",
            ].join(" ")}
          >
            {isSelected ? (
              <CircleCheck className="h-3.5 w-3.5" />
            ) : (
              <Square className="h-3.5 w-3.5" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Costo por m²
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground border-t border-border/40 pt-2">
          <div className="inline-flex items-center gap-1.5">
            <MapPin className="h-3 w-3 text-primary/60 shrink-0" />
            <span>Costo/m²</span>
            <span className="font-medium text-foreground">
              {formatSoles(tarifa.costo_por_m2)}
            </span>
          </div>
          <div className="inline-flex items-center gap-1.5">
            <Banknote className="h-3 w-3 text-primary/60 shrink-0" />
            <span>Der. mín.</span>
            <span className="font-medium text-foreground">
              {formatSoles(derecho?.derecho_minimo)}
            </span>
          </div>
          <div className="inline-flex items-center gap-1.5">
            <Banknote className="h-3 w-3 text-primary/60 shrink-0" />
            <span>Der. máx.</span>
            <span className="font-medium text-foreground">
              {formatSoles(derecho?.derecho_maximo)}
            </span>
          </div>
        </div>
      </button>
    </div>
  );
}
