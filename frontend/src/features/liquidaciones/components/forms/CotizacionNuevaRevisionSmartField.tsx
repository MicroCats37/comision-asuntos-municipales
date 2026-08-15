"use client";

import { useMutation } from "@tanstack/react-query";
import { Calculator, Loader2 } from "lucide-react";
/**
 * CotizacionNuevaRevisionSmartField — Smart Field de cotización para NUEVA REVISIÓN.
 *
 * A diferencia del CotizacionPorcentajeSmartField (que depende de useWatch del form),
 * este recibe el valor_declarado FIJO (heredado de la previa) y la tarifa seleccionada
 * como props — sin depender del form para cotizar.
 *
 * Auto-recalcula con debounce cuando cambia la tarifa seleccionada.
 */
import { useEffect, useState } from "react";
import { useDebounce } from "@/hooks/system/useDebounce";
import api from "@/lib/api";
import type { CotizacionOutput } from "../../schemas/cotizacion.schema";

interface CotizacionNuevaRevisionSmartFieldProps {
  /** Valor declarado FIJO heredado de la previa */
  valorDeclarado: number | undefined;
  /** Tarifa única seleccionada */
  tarifaId: string | null;
  /** Especialidades seleccionadas (checkbox) */
  especialidadesIds: string[];
}

const toNumber = (value: unknown): number => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};
const formatSoles = (value: unknown): string =>
  `S/ ${toNumber(value).toFixed(2)}`;

export function CotizacionNuevaRevisionSmartField({
  valorDeclarado,
  tarifaId,
  especialidadesIds,
}: CotizacionNuevaRevisionSmartFieldProps) {
  const [quote, setQuote] = useState<CotizacionOutput | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cotizacionMutation = useMutation({
    mutationFn: async (payload: {
      valor_declarado: number;
      tarifa_id: string;
      especialidades_ids: string[];
    }): Promise<CotizacionOutput> => {
      const { data } = await api.post("/liquidaciones/edificaciones/cotizar", {
        liquidacion_especifica: {
          datos: { valor_declarado: payload.valor_declarado },
          tarifas: payload.especialidades_ids.map((espId) => ({
            tarifa_porcentaje_obra_id: payload.tarifa_id,
            especialidad_id: espId,
          })),
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

  const debouncedTarifa = useDebounce(tarifaId, 400);
  const debouncedEspecialidades = useDebounce(especialidadesIds, 400);

  // Auto-recalculate when the selected tariff or especialidades change (debounced)
  useEffect(() => {
    const v = toNumber(valorDeclarado);

    if (
      !v ||
      v <= 0 ||
      !debouncedTarifa ||
      debouncedEspecialidades.length === 0
    ) {
      setQuote(null);
      setError(null);
      return;
    }

    cotizacionMutation.mutate({
      valor_declarado: v,
      tarifa_id: debouncedTarifa,
      especialidades_ids: debouncedEspecialidades,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedTarifa, debouncedEspecialidades, valorDeclarado]);

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

      {quote && (
        <div className="space-y-2 rounded-lg border border-border bg-card p-3">
          <div className="grid grid-cols-2 gap-1 text-sm">
            <span className="text-muted-foreground">% Liquidación:</span>
            <span className="font-medium text-right">
              {(toNumber(quote.porcentaje_liquidacion) * 100).toFixed(2)}%
            </span>
            <span className="text-muted-foreground">Subtotal:</span>
            <span className="font-medium text-right">
              {formatSoles(quote.total_subtotal)}
            </span>
          </div>
          <div className="border-t border-border pt-1.5 flex justify-between font-semibold text-sm">
            <span>Total a Pagar:</span>
            <span className="text-primary">{formatSoles(quote.total)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
