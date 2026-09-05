"use client";

import { useMutation } from "@tanstack/react-query";
import { Calculator, CheckCircle2, Loader2, XCircle } from "lucide-react";
/**
 * CotizacionVisitasSmartField — Smart Field for Visitas cotizacion preview.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<VisitasFormData>` from parent
 * - Reads `cantidad_visitas`, `categoria`, `tarifa_visitas_id` from form
 * - "Calcular" button triggers POST /liquidaciones/inspeccion-obra/cotizar (create)
 *   or POST /liquidaciones/inspeccion-obra/{id}/cotizar-edicion (edit)
 * - Shows result in its OWN state
 *
 * Backend response shape (CotizarPorCategoriaVisitasOutputSchema via present_cotizacion):
 * {
 *   datos: {
 *     entrada: { datos: { cantidad_visitas, categoria }, tarifa: { tarifa_visitas_id } },
 *     tarifa: { id, costo_por_visita },
 *     variables_financieras: { igv, uit }
 *   },
 *   calculo: { monto_bruto, subtotal, total }
 * }
 */
import { useCallback, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { notify } from "@/errors";
import api from "@/lib/api";

// ── Output type matching backend CotizarPorCategoriaVisitasOutputSchema ─────────

interface CotizacionVisitasQuote {
  datos: {
    entrada: {
      datos: {
        cantidad_visitas: number;
        categoria: string;
      };
      tarifa: {
        tarifa_visitas_id: string;
      };
    };
    tarifa: {
      id: string;
      costo_por_visita: number;
    };
    variables_financieras: {
      igv: number;
      uit: number;
    };
  };
  calculo: {
    monto_bruto: number;
    subtotal: number;
    total: number;
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface CotizacionVisitasSmartFieldProps {
  methods: UseFormReturn<any>;
  /** Edit mode calls /{id}/cotizar-edicion and sends liquidacion_tipo wrapper */
  mode?: "create" | "edit";
  liquidacionId?: string;
}

const formatSoles = (value: unknown): string => {
  const num = Number(value);
  return Number.isNaN(num) ? "S/ 0.00" : `S/ ${num.toFixed(2)}`;
};

export function CotizacionVisitasSmartField({
  methods,
  mode = "create",
  liquidacionId,
}: CotizacionVisitasSmartFieldProps) {
  // Own state — does not cause form re-render
  const [quote, setQuote] = useState<CotizacionVisitasQuote | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cotizacionMutation = useMutation({
    mutationFn: async (payload: {
      cantidad_visitas: number;
      categoria: string;
      tarifa_visitas_id: string;
    }): Promise<CotizacionVisitasQuote> => {
      const endpoint =
        mode === "edit" && liquidacionId
          ? `/liquidaciones/inspeccion-obra/${liquidacionId}/cotizar-edicion`
          : `/liquidaciones/inspeccion-obra/cotizar`;

      const body =
        mode === "edit"
          ? {
              liquidacion_tipo: {
                datos: {
                  cantidad_visitas: payload.cantidad_visitas,
                  categoria: payload.categoria,
                },
                tarifa: { tarifa_visitas_id: payload.tarifa_visitas_id },
              },
            }
          : {
              liquidacion: {
                cantidad_visitas: payload.cantidad_visitas,
                categoria: payload.categoria,
                tarifas_ids: [payload.tarifa_visitas_id],
              },
            };

      const { data } = await api.post(endpoint, body);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data as any).data as CotizacionVisitasQuote;
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
      tarifa_visitas_id: tarifaVisitasId,
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
        {isLoading && (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
        )}
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
                {quote.datos.entrada.datos.cantidad_visitas} (
                {quote.datos.entrada.datos.categoria})
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Costo/visita:</span>
              <span className="font-medium">
                {formatSoles(quote.datos.tarifa.costo_por_visita)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Subtotal:</span>
              <span className="font-medium">
                {formatSoles(quote.calculo.subtotal)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">IGV (18%):</span>
              <span className="font-medium">
                {formatSoles(quote.calculo.total - quote.calculo.subtotal)}
              </span>
            </div>
            <div className="flex justify-between border-t border-border pt-1.5 font-semibold">
              <span>Total:</span>
              <span className="text-primary">
                {formatSoles(quote.calculo.total)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
