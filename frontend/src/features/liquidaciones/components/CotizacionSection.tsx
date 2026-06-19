"use client";

import { Calculator, AlertCircle } from "lucide-react";
import type { CotizacionQuote, VariablesFinancieras } from "../types/liquidacion-edificaciones";
import { Button } from "@/components/ui/button";
import { VariablesFinancierasCard } from "./VariablesFinancierasCard";

interface CotizacionSectionProps {
  quote: CotizacionQuote | null;
  isLoading: boolean;
  onCotizar: () => void;
  hasErrors: boolean;
  /** Project must be selected/created */
  hasProject: boolean;
  /** valor_proyecto must be > 0 */
  hasValidValorProyecto: boolean;
  /** Financial variables data */
  variablesFinancieras?: VariablesFinancieras;
  isLoadingVariables?: boolean;
}

export function CotizacionSection({
  quote,
  isLoading,
  onCotizar,
  hasErrors,
  hasProject,
  hasValidValorProyecto,
  variablesFinancieras,
  isLoadingVariables,
}: CotizacionSectionProps) {
  const hasVariablesFinancieras = !!variablesFinancieras;

  // Button is disabled if any required field is missing or there are form errors
  const isDisabled =
    isLoading ||
    hasErrors ||
    !hasProject ||
    !hasValidValorProyecto ||
    !hasVariablesFinancieras;

  return (
    <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4">
      <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
        <Calculator className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide">
          Cotización / Resumen de Cálculo
        </h3>
      </div>

      {/* Variables Financieras Card - now inside CotizacionSection */}
      <VariablesFinancierasCard
        variables={variablesFinancieras}
        isLoading={isLoadingVariables}
      />

      {/* Botón Calcular Cotización */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Genera un resumen del cálculo sin guardar la liquidación.
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCotizar}
          disabled={isDisabled}
          className="gap-2 h-9 rounded-lg"
        >
          <Calculator className="h-4 w-4" />
          {isLoading ? "Calculando..." : "Calcular cotización"}
        </Button>
      </div>

      {/* Disabled reason hint */}
      {isDisabled && !isLoading && (
        <div className="flex gap-2 text-xs text-muted-foreground">
          {!hasProject && <span>• Selecciona o crea un proyecto</span>}
          {!hasValidValorProyecto && <span>• Ingresa un valor de proyecto válido</span>}
          {!hasVariablesFinancieras && <span>• Variables financieras no disponibles</span>}
        </div>
      )}

      {/* Resumen de Cotización */}
      {quote && (
        <div className="space-y-3 border-t pt-3">
          {/* Header */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="text-sm font-medium">
              Revisión #{quote.numero_revision}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                UIT: S/ {quote._metadata.uit_valor.toFixed(2)}
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
                      className="flex flex-col gap-1 text-sm pl-2 border-l-2 border-primary/30"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-foreground">
                          {rev.especialidad}
                        </span>
                        <span className="font-medium">
                          S/ {rev.monto_base.toFixed(2)}
                        </span>
                      </div>
                      {/* Tarifa details */}
                      <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground pl-1">
                        <span>
                          Derecho mín: S/ {rev.tarifa.derecho_minimo.toFixed(2)}
                        </span>
                        <span>
                          Derecho máx:{" "}
                          {rev.tarifa.derecho_maximo !== null
                            ? `S/ ${rev.tarifa.derecho_maximo.toFixed(2)}`
                            : "Sin máximo"}
                        </span>
                        <span>
                          % UIT mín: {(rev.tarifa.porcentaje_minimo_uit * 100).toFixed(1)}%
                        </span>
                      </div>
                      {!rev.cobra && (
                        <span className="text-xs text-muted-foreground italic">
                          (no cobra)
                        </span>
                      )}
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
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Total</span>
              <span>S/ {quote.totales.total.toFixed(2)}</span>
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
