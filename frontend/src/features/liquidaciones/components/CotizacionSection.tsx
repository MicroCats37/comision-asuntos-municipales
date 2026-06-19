"use client";

import { Calculator, AlertCircle } from "lucide-react";
import type { CotizacionQuote } from "../types/liquidacion-edificaciones";
import { Button } from "@/components/ui/button";

interface CotizacionSectionProps {
  quote: CotizacionQuote | null;
  isLoading: boolean;
  onCotizar: () => void;
  hasErrors: boolean;
}

export function CotizacionSection({
  quote,
  isLoading,
  onCotizar,
  hasErrors,
}: CotizacionSectionProps) {
  return (
    <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
      <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
        <Calculator className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide">
          Cotización / Resumen de Cálculo
        </h3>
      </div>

      {/* Botón Calcular Cotización */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Genera un resumen del cálculo sin guardar la liquidación.
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCotizar}
          disabled={isLoading || hasErrors}
          className="gap-2 h-9 rounded-lg"
        >
          <Calculator className="h-4 w-4" />
          {isLoading ? "Calculando..." : "Calcular cotización"}
        </Button>
      </div>

      {/* Resumen de Cotización */}
      {quote && (
        <div className="space-y-3 border-t pt-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">
              Revisión #{quote.numero_revision}
            </span>
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                quote._metadata.cobra
                  ? "bg-green-100 text-green-800"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {quote._metadata.cobra ? "Cobra" : "No cobra"}
            </span>
          </div>

          {/* Revisiones */}
              {quote.revisiones.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground">
                    Revisiones
                  </h4>
                  {quote.revisiones.map((rev) => (
                    <div
                      key={rev.id}
                      className="flex items-center justify-between text-sm pl-2 border-l-2 border-primary/30"
                    >
                      <span className="text-muted-foreground">
                        {rev.especialidad}
                      </span>
                      <div className="text-right">
                        <span className="font-medium">
                          S/ {rev.monto_base.toFixed(2)}
                        </span>
                        {!rev.cobra && (
                          <span className="text-xs text-muted-foreground ml-1">
                            (no cobra)
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

          {/* Totales */}
          <div className="space-y-1 border-t pt-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Subtotal</span>
              <span>S/ {quote.totales.subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">
                IGV ({quote._metadata.igv_valor * 100}%)
              </span>
              <span>S/ {quote.totales.igv.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-base font-semibold border-t pt-1">
              <span>Total a Pagar</span>
              <span className="text-primary">
                S/ {quote.totales.total_a_pagar.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Info sobre la cotización */}
          <p className="text-xs text-muted-foreground italic">
            Esta cotización es un estimado. El monto final se confirmará al crear
            la liquidación.
          </p>
        </div>
      )}

      {/* No hay cotización aún */}
      {!quote && !isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground italic">
          <AlertCircle className="h-4 w-4" />
          Presiona &quot;Calcular cotización&quot; para ver el resumen del cálculo.
        </div>
      )}
    </div>
  );
}
