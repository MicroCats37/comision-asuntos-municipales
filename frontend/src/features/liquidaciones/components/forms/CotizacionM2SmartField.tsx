"use client";

/**
 * CotizacionM2SmartField — Smart Field for M2 cotizacion preview.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<M2FormData>` from parent
 * - Reads `area_solicitada` and `tarifa_m2_id` from form
 * - "Calcular" button triggers POST /liquidaciones/{tipo}/cotizar
 * - Shows result: subtotal, IGV, total in its OWN state
 * - Does NOT write back to form until user confirms
 */
import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import type { UseFormReturn } from "react-hook-form";
import { Calculator, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { notify } from "@/errors";
import api from "@/lib/api";
import type { M2FormData } from "../../schemas/liquidacion-m2-form.schema";

interface CotizacionResult {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

interface CotizacionM2Quote {
  numero_revision: number;
  calculo_m2: {
    area_solicitada: number;
    area_base_calculo: number;
    derecho: number;
  };
  totales: CotizacionResult;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface CotizacionM2SmartFieldProps {
  methods: UseFormReturn<any>;
  tipo?: "habilitacion-urbana" | "mecanica-suelos";
}

const formatSoles = (value: number): string => `S/ ${value.toFixed(2)}`;

export function CotizacionM2SmartField({
  methods,
  tipo = "habilitacion-urbana",
}: CotizacionM2SmartFieldProps) {
  // Own state — does not cause form re-render
  const [quote, setQuote] = useState<CotizacionM2Quote | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cotizacionMutation = useMutation({
    mutationFn: async (payload: {
      area_solicitada: number;
      tarifas_ids: string[];
    }): Promise<CotizacionM2Quote> => {
      const { data } = await api.post(`/liquidaciones/${tipo}/cotizar`, {
        liquidacion: payload,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data as any).data;
    },
    onSuccess: (result) => {
      setQuote(result);
      setError(null);
    },
    onError: (err) => {
      setQuote(null);
      setError(err instanceof Error ? err.message : "Error al calcular cotización");
      notify.error("Error al calcular la cotización");
    },
  });

  const handleCalcular = useCallback(() => {
    const valores = methods.getValues();
    const areaSolicitada = valores.area_solicitada;
    const tarifaM2Id = valores.tarifa_m2_id;

    if (!areaSolicitada || areaSolicitada <= 0) {
      notify.error("Ingresa un área solicitada válida");
      return;
    }

    if (!tarifaM2Id) {
      notify.error("Selecciona una tarifa");
      return;
    }

    cotizacionMutation.mutate({
      area_solicitada: areaSolicitada,
      tarifas_ids: [tarifaM2Id],
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
              <span className="text-muted-foreground">Área:</span>
              <span className="font-medium">
                {quote.calculo_m2.area_solicitada} m²
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
