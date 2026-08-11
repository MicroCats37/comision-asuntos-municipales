"use client";

/**
 * TarifasM2SmartField — Smart Field for M2 tariff selection.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<M2FormData>` from parent
 * - Fetches vigentes from GET /liquidaciones/{tipo}/tarifas/vigentes
 * - Shows costo_por_m2 + derecho_minimo/maximo
 * - Single select (card), sets `tarifa_m2_id` via setValue
 */
import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import type { UseFormReturn } from "react-hook-form";
import { Banknote, CircleCheck, MapPin, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import type { M2FormData } from "../../schemas/liquidacion-m2-form.schema";

interface TarifaVigenteM2 {
  id: string;
  costo_por_m2: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  habilitada: boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface TarifasM2SmartFieldProps {
  methods: UseFormReturn<any>;
  tipo?: "habilitacion-urbana" | "mecanica-suelos";
}

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

export function TarifasM2SmartField({
  methods,
  tipo = "habilitacion-urbana",
}: TarifasM2SmartFieldProps) {
  // Own state — does not cause form re-render
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: tarifas, isLoading } = useQuery<TarifaVigenteM2[]>({
    queryKey: ["liquidaciones", tipo, "tarifas-vigentes"],
    queryFn: async () => {
      const { data } = await api.get(`/liquidaciones/${tipo}/tarifas/vigentes`);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data as any).data?.tarifas || [];
    },
  });

  const handleSelect = useCallback(
    (id: string) => {
      const isSelected = selectedId === id;
      const next = isSelected ? null : id;
      setSelectedId(next);
      methods.setValue("tarifa_m2_id", next || undefined, { shouldValidate: false });
    },
    [methods, selectedId],
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

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">Tarifas Vigentes</label>
      <div className="flex flex-col md:flex-row md:flex-wrap gap-2">
        {tarifas.map((tarifa) => {
          const isSelected = selectedId === tarifa.id;
          const isDisabled = !tarifa.habilitada;

          return (
            <button
              key={tarifa.id}
              type="button"
              disabled={isDisabled}
              onClick={() => !isDisabled && handleSelect(tarifa.id)}
              className={[
                "rounded-lg border bg-card px-3 py-2 transition-all duration-200 text-left w-full md:flex-1 md:min-w-[280px] flex flex-col gap-2",
                isSelected
                  ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                  : "border-border hover:border-primary/40 cursor-pointer",
                isDisabled && "opacity-50 cursor-not-allowed",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {/* Indicador de estado */}
              <div className="flex items-start gap-2 min-w-0">
                <div
                  className={[
                    "flex items-center justify-center rounded-md border shrink-0 p-1 mt-0.5",
                    isSelected
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-muted text-muted-foreground border-border",
                    isDisabled && "bg-muted/50 text-muted-foreground/50",
                  ].join(" ")}
                >
                  {isSelected ? (
                    <CircleCheck className="h-3.5 w-3.5" />
                  ) : (
                    <Square className="h-3.5 w-3.5" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <Badge
                    variant={isSelected ? "default" : "secondary"}
                    className="text-[10px] font-medium px-1.5 py-0.5"
                  >
                    Tarifa M2
                  </Badge>
                </div>
              </div>

              {/* Métricas compactas */}
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
                    {formatSoles(tarifa.derecho_minimo)}
                  </span>
                </div>
                <div className="inline-flex items-center gap-1.5">
                  <Banknote className="h-3 w-3 text-primary/60 shrink-0" />
                  <span>Der. máx.</span>
                  <span className="font-medium text-foreground">
                    {tarifa.derecho_maximo != null
                      ? formatSoles(tarifa.derecho_maximo)
                      : "—"}
                  </span>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
