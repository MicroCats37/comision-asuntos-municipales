"use client";

import { useMutation } from "@tanstack/react-query";
import { Calculator, CheckCircle2, Loader2, XCircle } from "lucide-react";
/**
 * CotizacionVisitasSmartField — Smart Field for Visitas cotizacion preview.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<VisitasFormData>` from parent
 * - Reads `cantidad_visitas`, `categoria`, `tarifa_visitas_id` from form
 * - "Calcular" button triggers POST /liquidaciones/inspeccion-obra/cotizar
 * - Shows result in its OWN state
 */
import { useCallback, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { notify } from "@/errors";
import api from "@/lib/api";
import type { VisitasFormData } from "../../schemas/liquidacion-visitas-form.schema";

interface CotizacionResult {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

interface CotizacionVisitasQuote {
  numero_revision: number;
  calculo_visitas: {
    cantidad_visitas: number;
    visitas_base_calculo: number;
    derecho: number;
    categoria: string;
  };
  totales: CotizacionResult;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface CotizacionVisitasSmartFieldProps {
  methods: UseFormReturn<any>;
}

const formatSoles = (value: number): string => `S/ ${value.toFixed(2)}`;

export function CotizacionVisitasSmartField({
  methods,
}: CotizacionVisitasSmartFieldProps) {
  // Own state — does not cause form re-render
  const [quote, setQuote] = useState<CotizacionVisitasQuote | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cotizacionMutation = useMutation({
    mutationFn: async (payload: {
      cantidad_visitas: number;
      categoria: string;
      tarifas_ids: string[];
    }): Promise<CotizacionVisitasQuote> => {
      const { data } = await api.post(
        "/liquidaciones/inspeccion-obra/cotizar",
        {
          liquidacion: payload,
        },
      );
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data as any).data;
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
      notify.error("Error al calcular la cotización");
    },
  });

  const handleCalcular = useCallback(() => {
    const valores = methods.getValues();
    const cantidadVisitas = valores.cantidad_visitas;
    const categoria = valores.categoria;
    const tarifaVisitasId = valores.tarifa_visitas_id;

    if (!cantidadVisitas || cantidadVisitas <= 0) {
      notify.error("Ingresa una cantidad de visitas válida");
      return;
    }

    if (!categoria) {
      notify.error("Selecciona una categoría");
      return;
    }

    if (!tarifaVisitasId) {
      notify.error("Selecciona una tarifa");
      return;
    }

    cotizacionMutation.mutate({
      cantidad_visitas: cantidadVisitas,
      categoria,
      tarifas_ids: [tarifaVisitasId],
    });
  }, [methods, cotizacionMutation]);

  const isLoading = cotizacionMutation.isPending;

  return (
    <div className="space-y-3 rounded-xl border border-primary/20 bg-primary/[0.03] p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <Calculator className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
          Cotización
        </h3>
      </div>

      <Button
        type="button"
        onClick={handleCalcular}
        disabled={isLoading}
        className="w-full"
      >
        {isLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Calculando...
          </>
        ) : (
          <>
            <Calculator className="h-4 w-4" />
            Calcular Cotización
          </>
        )}
      </Button>

      {error && (
        <div className="flex items-center gap-2 text-sm text-destructive">
          <XCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      {quote && (
        <div className="space-y-2 rounded-lg border border-border bg-card p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-4 w-4" />
            <span>Cotización Calculada</span>
          </div>

          <div className="space-y-1.5 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Visitas:</span>
              <span className="font-medium">
                {quote.calculo_visitas.cantidad_visitas} (
                {quote.calculo_visitas.categoria})
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Subtotal:</span>
              <span className="font-medium">
                {formatSoles(quote.totales.subtotal)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">IGV (18%):</span>
              <span className="font-medium">
                {formatSoles(quote.totales.igv)}
              </span>
            </div>
            <div className="flex justify-between border-t border-border pt-1.5 font-semibold">
              <span>Total:</span>
              <span className="text-primary">
                {formatSoles(quote.totales.total)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
