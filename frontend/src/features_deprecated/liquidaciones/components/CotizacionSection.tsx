"use client";

import { AlertCircle, Calculator, Receipt, BadgeCheck, CircleCheck, Percent, Banknote } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FormSectionHeader } from "@/components-app/forms/FormSectionHeader";
import type {
  CotizacionQuote,
  VariablesFinancieras,
} from "../types/liquidacion-edificaciones";
import { VariablesFinancierasCard } from "./VariablesFinancierasCard";

interface TarifaReference {
  porcentaje_liquidacion: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  especialidades: Array<{ id: string; nombre: string }>;
}

interface CotizacionSectionProps {
  quote: CotizacionQuote | null;
  isLoading: boolean;
  onCotizar: () => void;
  hasErrors: boolean;
  hasValidValorBase?: boolean;
  hasTarifa?: boolean;
  isLoadingData?: boolean;
  variablesFinancieras?: VariablesFinancieras;
  isLoadingVariables?: boolean;
  compact?: boolean;
  hideButton?: boolean;
  valorBaseActual?: number;
  tarifaSeleccionada?: TarifaReference | null;
  revisionLabel?: string | null;
}

const formatSoles = (value?: number | null): string => {
  if (value == null || Number.isNaN(value)) return "S/ 0.00";
  return `S/ ${value.toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

const formatPercent = (value?: number | null): string => {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(2)}%`;
};

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
  compact = false,
  hideButton = false,
  valorBaseActual,
  tarifaSeleccionada,
  revisionLabel,
}: CotizacionSectionProps) {
  const hasVariablesFinancieras = !!variablesFinancieras;
  const valorBaseCotizado = quote?._metadata?.valor_base_calculo;
  const hasValorDesactualizado =
    quote &&
    valorBaseActual != null &&
    Math.abs(valorBaseActual - (valorBaseCotizado ?? 0)) > 0.009;

  const isDisabled =
    isLoading || isLoadingData || hasErrors || !hasVariablesFinancieras
    || (hasValidValorBase !== undefined && !hasValidValorBase)
    || (hasTarifa !== undefined && !hasTarifa);

  return (
    <div className={compact ? "space-y-2" : "space-y-4"}>
      {!compact && (
        <FormSectionHeader
          title="Cotización / Resumen de Cálculo"
          icon={Calculator}
          variant="soft"
        />
      )}

      {/* Botón Calcular Cotización */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {isLoading
            ? "Calculando cotización..."
            : quote
              ? "Cotización lista"
              : hideButton
                ? "Presiona Enter en el valor del proyecto para cotizar"
                : "Presiona Enter en el valor o el botón para cotizar"}
        </p>
        {!quote && (
          <VariablesFinancierasCard
            variables={variablesFinancieras}
            isLoading={isLoadingVariables}
          />
        )}
        {!hideButton && (
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
        )}
      </div>

      {/* Status hints — always visible to prevent layout shift */}
      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground min-h-[1.5rem]">
        {isLoadingData && (
          <span>• Cargando datos...</span>
        )}
        {!hasVariablesFinancieras && !isLoadingData && (
          <span>• Variables financieras no disponibles</span>
        )}
        {hasValidValorBase !== undefined && !hasValidValorBase && !isLoadingData && (
          <span>• Ingresa un valor de proyecto válido</span>
        )}
        {hasTarifa !== undefined && !hasTarifa && !isLoadingData && (
          <span>• Selecciona una tarifa</span>
        )}
      </div>

      {hasValorDesactualizado && (
        <p className="flex items-center gap-1.5 rounded-lg border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs font-medium text-destructive">
          <AlertCircle className="h-3.5 w-3.5" />
          Valor actual {formatSoles(valorBaseActual)}. Presiona Enter para actualizar la cotización.
        </p>
      )}

      {!quote && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div
            className={[
              "rounded-lg border p-3 text-sm bg-card",
              hasValorDesactualizado
                ? "border-destructive/40 bg-destructive/5"
                : "border-border",
            ].join(" ")}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Valor usado para cotizar
                </p>
                <p className="mt-1 text-base font-semibold">
                  {formatSoles(valorBaseCotizado ?? valorBaseActual)}
                </p>
              </div>
              {hasValorDesactualizado && (
                <Badge variant="outline" className="border-destructive/40 text-destructive bg-background">
                  Pendiente
                </Badge>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-3 text-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Tarifa seleccionada
            </p>
            {tarifaSeleccionada ? (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>Liq. <strong className="text-foreground">{formatPercent(tarifaSeleccionada.porcentaje_liquidacion)}</strong></span>
                {tarifaSeleccionada.especialidades.map((e) => (
                  <Badge key={e.id} variant="secondary" className="text-[10px]">
                    {e.nombre}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="mt-1 text-xs text-muted-foreground">Sin tarifa seleccionada</p>
            )}
          </div>
        </div>
      )}

      {/* Resumen de Cotización */}
      {quote && (
        <div className="space-y-3 border-t pt-3">
          {/* Header */}
          <div className="rounded-lg border border-border bg-card px-3 py-2 space-y-2">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-2 min-w-0">
                <div className="flex items-center justify-center rounded-md border bg-primary text-primary-foreground border-primary shrink-0 p-1 mt-0.5">
                  <CircleCheck className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {revisionLabel !== null && (
                      <span className="text-sm font-medium mr-1">
                        {revisionLabel ?? `Revisión #${quote.numero_revision}`}
                      </span>
                    )}
                    {tarifaSeleccionada?.especialidades.map((e) => (
                      <Badge key={e.id} variant="default" className="text-[10px] font-medium px-1.5 py-0.5">
                        {e.nombre}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
              <VariablesFinancierasCard
                variables={variablesFinancieras}
                isLoading={isLoadingVariables}
              />
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground border-t border-border/40 pt-2">
              <div className="inline-flex items-center gap-1.5">
                <Banknote className="h-3 w-3 text-primary/60 shrink-0" />
                <span>Valor</span>
                <span className="font-medium text-foreground">
                  {formatSoles(valorBaseCotizado ?? valorBaseActual)}
                </span>
              </div>
              {tarifaSeleccionada && (
                <div className="inline-flex items-center gap-1.5">
                  <Percent className="h-3 w-3 text-primary/60 shrink-0" />
                  <span>Liq.</span>
                  <span className="font-medium text-foreground">
                    {formatPercent(tarifaSeleccionada.porcentaje_liquidacion)}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Revisiones — hidden in compact mode */}
          {!compact && quote.revisiones.length > 0 && (
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
                        {rev.monto_base != null ? formatSoles(rev.monto_base) : "—"}
                      </span>
                    </div>

                    {/* Tarifa details */}
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground border-t border-border/50 pt-2">
                      <span>
                        Der. mín: {rev.tarifa?.derecho_minimo != null ? formatSoles(rev.tarifa.derecho_minimo) : "—"}
                      </span>
                      <span>
                        Der. máx:{" "}
                        {rev.tarifa?.derecho_maximo != null
                          ? formatSoles(rev.tarifa.derecho_maximo)
                          : "Sin máximo"}
                      </span>
                      <span>
                        % UIT mín:{" "}
                        {rev.tarifa?.porcentaje_minimo_uit != null
                          ? (rev.tarifa.porcentaje_minimo_uit * 100).toFixed(1)
                          : "—"}%
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
              <span className="font-medium">{formatSoles(quote.totales.subtotal)}</span>
            </div>
            <div className="flex flex-col gap-1 text-sm p-3 rounded-lg border border-border bg-card">
              <span className="text-muted-foreground text-xs">
                IGV ({quote._metadata.igv_valor * 100}%)
              </span>
              <span className="font-medium">{formatSoles(quote.totales.igv)}</span>
            </div>
            <div className="flex flex-col gap-1 text-sm p-3 rounded-lg border border-border bg-card">
              <span className="text-muted-foreground text-xs">Total</span>
              <span className="font-medium">{formatSoles(quote.totales.total)}</span>
            </div>
            <div className="flex flex-col gap-1.5 text-base font-bold p-4 rounded-lg border border-primary bg-primary/5">
              <span className="flex items-center gap-1.5 text-primary">
                <BadgeCheck className="h-4 w-4" />
                Total a Pagar
              </span>
              <span className="text-xl text-primary">
                {formatSoles(quote.totales.total_a_pagar)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
