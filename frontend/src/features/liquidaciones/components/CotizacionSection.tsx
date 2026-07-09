"use client";

import { AlertCircle, Calculator, Receipt, BadgeCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FormSectionHeader } from "@/components-app/forms/FormSectionHeader";
import type {
  CotizacionQuote,
  VariablesFinancieras,
} from "../types/liquidacion-edificaciones";
import { VariablesFinancierasCard } from "./VariablesFinancierasCard";

interface CotizacionSectionProps {
  quote: CotizacionQuote | null;
  isLoading: boolean;
  onCotizar: () => void;
  hasErrors: boolean;
  hasValidValorBase: boolean;
  hasTarifa?: boolean;
  isLoadingData?: boolean;
  variablesFinancieras?: VariablesFinancieras;
  isLoadingVariables?: boolean;
}

export function CotizacionSection({
  quote,
  isLoading,
  onCotizar,
  hasErrors,
  hasValidValorBase,
  hasTarifa,
  isLoadingData,
  variablesFinancieras,
  isLoadingVariables,
}: CotizacionSectionProps) {
  const hasVariablesFinancieras = !!variablesFinancieras;

  const isDisabled =
    isLoading || isLoadingData || hasErrors || !hasValidValorBase || !hasTarifa || !hasVariablesFinancieras;

  return (
    <div className="space-y-4">
      <FormSectionHeader
        title="Cotización / Resumen de Cálculo"
        icon={Calculator}
        variant="soft"
      />

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
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          {isLoadingData && (
            <span>• Cargando datos...</span>
          )}
          {!hasValidValorBase && (
            <span>• Ingresa un valor de proyecto válido</span>
          )}
          {!hasTarifa && (
            <span>• Selecciona exactamente una revisión/tarifa</span>
          )}
          {!hasVariablesFinancieras && (
            <span>• Variables financieras no disponibles</span>
          )}
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
                className={`text-xs px-2 py-1 rounded-full font-medium ${
                  quote._metadata.cobra
                    ? "bg-primary/10 text-primary"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                
              </span>
            </div>
          </div>

          {/* Revisiones */}
          {quote.revisiones.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase text-muted-foreground flex items-center gap-1.5">
                <Receipt className="h-3.5 w-3.5" />
                Revisiones
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {quote.revisiones.map((rev) => (
                  <div
                    key={rev.id}
                    className="flex flex-col gap-2 text-sm p-4 rounded-lg border border-border bg-card"
                  >
                    {/* Especialidades como badges */}
                    <div className="flex flex-wrap gap-1.5">
                      {rev.especialidades.map((e) => (
                        <Badge
                          key={e.id}
                          variant="secondary"
                          className="text-xs font-medium"
                        >
                          {e.nombre}
                        </Badge>
                      ))}
                    </div>

                    {/* Monto base destacado */}
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">Monto base</span>
                      <span className="font-semibold text-foreground">
                        S/ {rev.monto_base.toFixed(2)}
                      </span>
                    </div>

                    {/* Tarifa details */}
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground border-t border-border/50 pt-2">
                      <span>
                        Der. mín: S/ {rev.tarifa.derecho_minimo.toFixed(2)}
                      </span>
                      <span>
                        Der. máx:{" "}
                        {rev.tarifa.derecho_maximo !== null
                          ? `S/ ${rev.tarifa.derecho_maximo.toFixed(2)}`
                          : "Sin máximo"}
                      </span>
                      <span>
                        % UIT mín:{" "}
                        {(rev.tarifa.porcentaje_minimo_uit * 100).toFixed(1)}%
                      </span>
                    </div>
                    {!rev.cobra && (
                      <span className="text-xs text-muted-foreground italic flex items-center gap-1">
                        <AlertCircle className="h-3 w-3" />
                        (no cobra)
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Totales */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 border-t border-border pt-4">
            <div className="flex flex-col gap-1 text-sm p-3 rounded-lg border border-border bg-card">
              <span className="text-muted-foreground text-xs">Subtotal</span>
              <span className="font-medium">S/ {quote.totales.subtotal.toFixed(2)}</span>
            </div>
            <div className="flex flex-col gap-1 text-sm p-3 rounded-lg border border-border bg-card">
              <span className="text-muted-foreground text-xs">
                IGV ({quote._metadata.igv_valor * 100}%)
              </span>
              <span className="font-medium">S/ {quote.totales.igv.toFixed(2)}</span>
            </div>
            <div className="flex flex-col gap-1 text-sm p-3 rounded-lg border border-border bg-card">
              <span className="text-muted-foreground text-xs">Total</span>
              <span className="font-medium">S/ {quote.totales.total.toFixed(2)}</span>
            </div>
            <div className="flex flex-col gap-1.5 text-base font-bold p-4 rounded-lg border border-primary bg-primary/5">
              <span className="flex items-center gap-1.5 text-primary">
                <BadgeCheck className="h-4 w-4" />
                Total a Pagar
              </span>
              <span className="text-xl text-primary">
                S/ {quote.totales.total_a_pagar.toFixed(2)}
              </span>
            </div>
          </div>

          
        </div>
      )}

      {/* No hay cotización aún */}
      {!quote && !isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground italic">
          <AlertCircle className="h-4 w-4" />
          Presiona &quot;Calcular cotización&quot; para ver el resumen del
          cálculo.
        </div>
      )}
    </div>
  );
}
