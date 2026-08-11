"use client";

/**
 * TarifasVisitasSmartField — Smart Field for Visitas tariff selection.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<VisitasFormData>` from parent
 * - Fetches vigentes from GET /liquidaciones/inspeccion-obra/tarifas/vigentes
 * - Shows categorias with costo_por_visita
 * - Select categoria + tarifa, sets `categoria` and `tarifa_visitas_id`
 */
import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import type { UseFormReturn } from "react-hook-form";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import type { VisitasFormData } from "../../schemas/liquidacion-visitas-form.schema";

interface TarifaVigenteVisitas {
  id: string;
  costo_por_visita: number;
  visitas_minimas: number;
  categoria: string;
  habilitada: boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface TarifasVisitasSmartFieldProps {
  methods: UseFormReturn<any>;
}

function LoadingCard() {
  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-3 animate-pulse">
      <div className="h-4 w-40 bg-muted rounded" />
      <div className="grid grid-cols-2 gap-3">
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

export function TarifasVisitasSmartField({
  methods,
}: TarifasVisitasSmartFieldProps) {
  const { data: tarifas, isLoading } = useQuery<TarifaVigenteVisitas[]>({
    queryKey: ["liquidaciones", "inspeccion-obra", "tarifas-vigentes"],
    queryFn: async () => {
      const { data } = await api.get("/liquidaciones/inspeccion-obra/tarifas/vigentes");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data as any).data?.tarifas || [];
    },
  });

  // Group tarifas by categoria
  const groupedByCategoria = (tarifas || []).reduce<Record<string, TarifaVigenteVisitas[]>>(
    (acc, tarifa) => {
      if (!acc[tarifa.categoria]) {
        acc[tarifa.categoria] = [];
      }
      acc[tarifa.categoria].push(tarifa);
      return acc;
    },
    {},
  );

  const handleSelect = useCallback(
    (tarifa: TarifaVigenteVisitas) => {
      methods.setValue("categoria", tarifa.categoria as VisitasFormData["categoria"], {
        shouldValidate: false,
      });
      methods.setValue("tarifa_visitas_id", tarifa.id, { shouldValidate: false });
    },
    [methods],
  );

  if (isLoading) {
    return (
      <div className="space-y-2">
        <label className="text-sm font-medium">Tarifas por Categoría</label>
        <div className="flex flex-col gap-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <LoadingCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (!tarifas || tarifas.length === 0) {
    return (
      <div className="space-y-2">
        <label className="text-sm font-medium">Tarifas por Categoría</label>
        <p className="text-sm text-muted-foreground text-center py-4">
          No hay tarifas vigentes disponibles
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <label className="text-sm font-medium">Tarifas por Categoría</label>
      <div className="flex flex-col gap-4">
        {Object.entries(groupedByCategoria).map(([categoria, tarifasCategoria]) => (
          <div key={categoria} className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-sm font-bold px-3 py-1">
                {categoria}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {tarifasCategoria.length} tarifa(s)
              </span>
            </div>
            <div className="flex flex-col md:flex-row md:flex-wrap gap-2">
              {tarifasCategoria.map((tarifa) => {
                const isDisabled = !tarifa.habilitada;
                return (
                  <button
                    key={tarifa.id}
                    type="button"
                    disabled={isDisabled}
                    onClick={() => !isDisabled && handleSelect(tarifa)}
                    className={[
                      "rounded-lg border bg-card px-3 py-2 transition-all duration-200 text-left w-full md:flex-1 md:min-w-[200px] flex flex-col gap-1",
                      !isDisabled && "hover:border-primary/40 cursor-pointer",
                      isDisabled && "opacity-50 cursor-not-allowed",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  >
                    <div className="flex justify-between items-start">
                      <span className="text-sm font-medium text-foreground">
                        S/ {tarifa.costo_por_visita.toFixed(2)} /visita
                      </span>
                      <span className="text-xs text-muted-foreground">
                        mín. {tarifa.visitas_minimas}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
