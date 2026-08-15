"use client";

import { useMutation } from "@tanstack/react-query";
import { Calculator, Loader2 } from "lucide-react";
/**
 * CotizacionPorcentajeSmartField — Smart Field for cotizacion preview.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<EdificacionesFormData>` from parent
 * - Reads `valor_declarado` and `tarifas_ids` from form
 * - "Calcular" button triggers POST /liquidaciones/edificaciones/cotizar
 * - Shows result: subtotal, IGV, total in its OWN state
 * - Does NOT write back to form until user confirms
 */
import { useEffect, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { useDebounce } from "@/hooks/system/useDebounce";
import api from "@/lib/api";
import type { CotizacionOutput } from "../../schemas/cotizacion.schema";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface CotizacionPorcentajeSmartFieldProps {
  methods: UseFormReturn<any>;
  /** Tipo de liquidación para el endpoint de cotizar (default: edificaciones) */
  tipo?: string;
  /** Valor declarado FIJO (para nueva revisión — se hereda de la previa, no está en el form) */
  valorDeclaradoFijo?: number;
}

// Backend serializes Decimal as strings — coerce to Number defensively
const toNumber = (value: unknown): number => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

const formatSoles = (value: unknown): string =>
  `S/ ${toNumber(value).toFixed(2)}`;

export function CotizacionPorcentajeSmartField({
  methods,
  tipo = "edificaciones",
  valorDeclaradoFijo,
}: CotizacionPorcentajeSmartFieldProps) {
  const [quote, setQuote] = useState<CotizacionOutput | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cotizacionMutation = useMutation({
    mutationFn: async (payload: {
      valor_declarado: number;
      tarifa_id: string;
      especialidades_ids: string[];
    }): Promise<CotizacionOutput> => {
      const { data } = await api.post(`/liquidaciones/${tipo}/cotizar`, {
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

  // Auto-recalculate when valor_declarado changes (debounced). Empty especialidades = backend auto-fill.
  const valorDeclaradoForm = useWatch({
    control: methods.control,
    name: "valor_declarado",
  });
  const tarifaUnicaId = useWatch({
    control: methods.control,
    name: "tarifa_unica_id",
  });
  const especialidadesSeleccionadas = useWatch({
    control: methods.control,
    name: "especialidades_seleccionadas",
  });
  // Use fixed value (nueva revision) OR form value (primera revision)
  const effectiveValor = valorDeclaradoFijo ?? valorDeclaradoForm;
  const debouncedValor = useDebounce(effectiveValor, 500);

  useEffect(() => {
    const v = Number(debouncedValor);

    if (!v || v <= 0) {
      setQuote(null);
      setError(null);
      return;
    }

    const espIds = (especialidadesSeleccionadas || []) as string[];

    cotizacionMutation.mutate({
      valor_declarado: v,
      tarifa_id: tarifaUnicaId ?? "",
      especialidades_ids: espIds,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedValor, tarifaUnicaId, especialidadesSeleccionadas]);

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
              {(Number(quote.porcentaje_liquidacion) * 100).toFixed(2)}%
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
