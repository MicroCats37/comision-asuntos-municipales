"use client";

import { useMutation } from "@tanstack/react-query";
import { Calculator, Loader2 } from "lucide-react";
/**
 * CotizacionM2SmartField — Smart Field para preview de cotización M2 (HU, MS).
 *
 * Backend POST /liquidaciones/{tipo}/cotizar
 * Input: { liquidacion_especifica: { datos: { area_solicitada }, tarifa: { tarifa_m2_id } } }
 * Output: { datos: { entrada, tarifa, derecho, variables_financieras }, calculo: { monto_bruto, subtotal, total } }
 *
 * Auto-recalcula con debounce cuando cambian area_solicitada o tarifa_m2_id.
 */
import { useEffect, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { useDebounce } from "@/hooks/system/useDebounce";
import api from "@/lib/api";

interface CotizacionM2Output {
  datos?: {
    tarifa?: { id?: string; costo_por_m2?: number } | null;
    derecho?: {
      id?: string;
      derecho_minimo?: number;
      derecho_maximo?: number;
    } | null;
  } | null;
  calculo?: {
    monto_bruto?: number;
    subtotal?: number;
    total?: number;
  } | null;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface CotizacionM2SmartFieldProps {
  methods: UseFormReturn<any>;
  tipo?: "habilitacion-urbana" | "mecanica-suelos";
}

const toNumber = (value: unknown): number => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};
const formatSoles = (value: unknown): string =>
  `S/ ${toNumber(value).toFixed(2)}`;

export function CotizacionM2SmartField({
  methods,
  tipo = "habilitacion-urbana",
}: CotizacionM2SmartFieldProps) {
  const [quote, setQuote] = useState<CotizacionM2Output | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cotizacionMutation = useMutation({
    mutationFn: async (payload: {
      area_solicitada: number;
      tarifa_m2_id: string;
    }): Promise<CotizacionM2Output> => {
      const { data } = await api.post(`/liquidaciones/${tipo}/cotizar`, {
        liquidacion_especifica: {
          datos: { area_solicitada: payload.area_solicitada },
          tarifa: { tarifa_m2_id: payload.tarifa_m2_id },
        },
      });
      return data.data;
    },
    onSuccess: (result) => {
      setQuote(result);
      setError(null);
    },
    onError: (err) => {
      setQuote(null);
      setError(
        err instanceof Error ? err.message : "Error al calcular cotización",
      );
    },
  });

  // Auto-recalculate when area or tarifa change (debounced)
  const areaSolicitada = useWatch({
    control: methods.control,
    name: "area_solicitada",
  });
  const tarifaM2Id = useWatch({
    control: methods.control,
    name: "tarifa_m2_id",
  });
  const debouncedArea = useDebounce(areaSolicitada, 500);

  useEffect(() => {
    const area = toNumber(debouncedArea);

    if (!area || area <= 0 || !tarifaM2Id) {
      setQuote(null);
      setError(null);
      return;
    }

    cotizacionMutation.mutate({
      area_solicitada: area,
      tarifa_m2_id: tarifaM2Id,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedArea, tarifaM2Id]);

  const isLoading = cotizacionMutation.isPending;

  return (
    <div className="space-y-3 rounded-xl border border-primary/20 bg-primary/[0.03] p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <Calculator className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
          Cotización
        </h3>
        {isLoading && (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
        )}
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}

      {isLoading && !quote && (
        <p className="text-xs text-muted-foreground animate-pulse">
          Calculando cotización...
        </p>
      )}

      {quote && quote.calculo && (
        <div className="space-y-2 rounded-lg border border-border bg-card p-3">
          <div className="grid grid-cols-2 gap-1 text-sm">
            <span className="text-muted-foreground">Costo/m²:</span>
            <span className="font-medium text-right">
              {formatSoles(quote.datos?.tarifa?.costo_por_m2)}
            </span>
            <span className="text-muted-foreground">Derecho mín.:</span>
            <span className="font-medium text-right">
              {formatSoles(quote.datos?.derecho?.derecho_minimo)}
            </span>
            <span className="text-muted-foreground">Subtotal:</span>
            <span className="font-medium text-right">
              {formatSoles(quote.calculo.subtotal)}
            </span>
          </div>
          <div className="border-t border-border pt-1.5 flex justify-between font-semibold text-sm">
            <span>Total a Pagar:</span>
            <span className="text-primary">
              {formatSoles(quote.calculo.total)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
