"use client";

/**
 * TaludesCotizacionSection — Cotizacion display for Taludes single-form modal.
 *
 * Pattern from HabilitacionUrbanaCotizacionSection, adapted to Taludes'
 * CotizacionTaludesResponse shape.
 *
 * Key differences from HU CotizacionSection:
 * - Shows Taludes-specific calculo_m2 fields (area_solicitada, derecho, tarifa)
 * - Cotizacion fires on Enter (caller controls via onCotizar)
 * - Show pending/out-of-sync indicator when area differs from quote
 * - Hide calculate button (caller uses Enter to cotizar)
 * - Compact layout variant
 */
import { AlertCircle, Banknote, Calculator, Loader2 } from "lucide-react";
import type { CotizacionTaludesResponse } from "../types/liquidacion-taludes.types";
import type { VariablesFinancieras } from "../types/liquidacion-edificaciones";

interface TaludesCotizacionSectionProps {
  quote: CotizacionTaludesResponse | null;
  isLoading: boolean;
  onCotizar: () => void;
  hasErrors: boolean;
  isLoadingData: boolean;
  variablesFinancieras?: VariablesFinancieras | null;
  isLoadingVariables: boolean;
  /** Current area_solicitada value in the form */
  areaSolicitadaActual: number;
  /** Hide the calculate button (Taludes uses Enter to cotizar) */
  hideButton?: boolean;
  /** Compact layout variant */
  compact?: boolean;
}

function formatSoles(value: number): string {
  return `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
}

function formatM2(value: number): string {
  return `${value.toLocaleString("es-PE")} m²`;
}

export function TaludesCotizacionSection({
  quote,
  isLoading,
  onCotizar,
  hasErrors,
  isLoadingData,
  variablesFinancieras,
  isLoadingVariables,
  areaSolicitadaActual,
  hideButton = false,
  compact = false,
}: TaludesCotizacionSectionProps) {
  // ── Pending / out-of-sync indicator ────────────────────────────────────────
  const areaBaseCalculo = quote?.calculo_m2?.area_base_calculo ?? null;
  const isOutOfSync =
    quote != null &&
    areaBaseCalculo != null &&
    areaSolicitadaActual !== areaBaseCalculo;

  const isLoadingAny = isLoading || isLoadingData;

  if (isLoadingAny && !quote) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground italic">
        <Loader2 className="h-4 w-4 animate-spin" />
        Cargando cotización...
      </div>
    );
  }

  if (hasErrors && !quote) {
    return (
      <div className="flex items-center gap-2 text-sm text-destructive">
        <AlertCircle className="h-4 w-4" />
        Error al calcular la cotización
      </div>
    );
  }

  if (!quote) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground italic">
        <Calculator className="h-4 w-4" />
        Escribe el área y presiona Enter para cotizar
      </div>
    );
  }

  const { calculo_m2, totales, _metadata } = quote;

  return (
    <div className={`space-y-3 ${compact ? "" : ""}`}>
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Calculator className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold text-foreground">
            Cotización
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {!isLoadingVariables && variablesFinancieras && (
            <>
              <span>
                IGV: {(Number(variablesFinancieras.igv_valor) * 100).toFixed(0)}%
              </span>
              <span>•</span>
              <span>
                UIT: {formatSoles(variablesFinancieras.uit_valor)}
              </span>
            </>
          )}
          {_metadata?.uit_valor != null && (
            <span className="ml-1">
              UIT: {formatSoles(_metadata.uit_valor)}
            </span>
          )}
        </div>
      </div>

      {/* Out-of-sync warning */}
      {isOutOfSync && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          <span>
            El área cambió. Presiona Enter en el campo Área para recalcular.
          </span>
        </div>
      )}

      {/* Area + Tarifa breakdown */}
      {calculo_m2 && (
        <div className={`space-y-2 rounded-lg border border-border bg-card p-3 ${compact ? "text-xs" : "text-sm"}`}>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Revisión</span>
            <span className="font-medium">#{quote.numero_revision}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Área solicitada</span>
            <span className="font-medium">{formatM2(calculo_m2.area_solicitada)}</span>
          </div>
          {calculo_m2.tarifa && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Costo / m²</span>
                <span className="font-medium">
                  {formatSoles(calculo_m2.tarifa.costo_por_m2)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Derecho mínimo</span>
                <span className="font-medium">
                  {formatSoles(calculo_m2.tarifa.derecho_minimo)}
                </span>
              </div>
              {calculo_m2.tarifa.derecho_maximo != null && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Derecho máximo</span>
                  <span className="font-medium">
                    {formatSoles(calculo_m2.tarifa.derecho_maximo)}
                  </span>
                </div>
              )}
            </>
          )}
          <div className="flex items-center justify-between border-t border-border/60 pt-2">
            <span className="text-muted-foreground">Derecho calculado</span>
            <span className="font-semibold">
              {formatSoles(calculo_m2.derecho)}
            </span>
          </div>
        </div>
      )}

      {/* Totals grid */}
      <div className={`grid grid-cols-2 gap-3 border-t border-border pt-3 ${compact ? "text-xs" : "text-sm"}`}>
        <div className="flex flex-col gap-1">
          <span className="text-muted-foreground text-xs">Subtotal</span>
          <span className="font-medium">{formatSoles(totales.subtotal)}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-muted-foreground text-xs">IGV</span>
          <span className="font-medium">{formatSoles(totales.igv)}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-muted-foreground text-xs">Total</span>
          <span className="font-medium">{formatSoles(totales.total)}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-muted-foreground text-xs">Liq. Total</span>
          <span className="font-medium">{formatSoles(totales.liquidacion_total)}</span>
        </div>
      </div>

      {/* Total a pagar — prominent */}
      <div className="flex items-center justify-between rounded-lg border border-primary bg-primary/5 p-3">
        <div className="flex items-center gap-2">
          <Banknote className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold text-primary">Total a Pagar</span>
        </div>
        <span className="text-lg font-bold text-primary">
          {formatSoles(totales.total_a_pagar)}
        </span>
      </div>

      {/* Hidden calculate button — caller uses Enter on area input instead */}
      {!hideButton && (
        <button
          type="button"
          onClick={onCotizar}
          disabled={isLoading}
          className="w-full h-10 rounded-xl font-semibold border border-border/60 hover:border-border hover:bg-background transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Calculando...
            </>
          ) : (
            <>
              <Calculator className="h-4 w-4" />
              Recalcular cotización
            </>
          )}
        </button>
      )}
    </div>
  );
}
