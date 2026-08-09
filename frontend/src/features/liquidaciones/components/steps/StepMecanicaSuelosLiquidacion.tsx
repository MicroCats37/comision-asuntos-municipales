/**
 * Step: Liquidación Mecánica de Suelos — Solo área + campos comunes + cotización + tarifas.
 * Versión específica para MS sin kind dispatch.
 */
"use client";

import { Banknote, Building2, Calculator, FileText, MapPin, MessageSquare, Tag } from "lucide-react";
import { useCallback, useEffect, useRef } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { FormSectionHeader } from "@/components-app/forms/FormSectionHeader";
import { notify } from "@/errors";
import { useMecanicaSuelosStepperStore } from "../../store";
import type { CotizacionMecanicaSuelosResponse } from "../../types/liquidacion-mecanica-suelos.types";
import { useTarifasVigentesMecanicaSuelos } from "../../hooks/useTarifasVigentes";

interface StepMecanicaSuelosLiquidacionProps {
  methods: UseFormReturn<FieldValues>;
  isActive: boolean;
  municipalidades: Array<{
    id: string;
    codigo?: string | null;
    nombre: string;
    provincia?: { nombre: string } | null;
    distrito?: { nombre: string } | null;
  }>;
  isLoadingMunicipalidades: boolean;
  /** Cotizar mutation */
  cotizarMutation: {
    mutateAsync: (
      payload: { area_solicitada: number; tarifas_ids: string[] },
    ) => Promise<CotizacionMecanicaSuelosResponse>;
    isPending: boolean;
  };
  quote: CotizacionMecanicaSuelosResponse | null;
  setCotizacionQuote: (quote: CotizacionMecanicaSuelosResponse | null) => void;
  setCotizacionError: (error: string | null) => void;
  setCotizacionCalculating: (val: boolean) => void;
}

function formatMunicipalidadLabel(m: {
  codigo?: string | null;
  nombre: string;
  provincia?: { nombre: string } | null;
  distrito?: { nombre: string } | null;
}) {
  const args: string[] = [];
  if (m.codigo) args.push(m.codigo);
  args.push(m.nombre);
  const sub: string[] = [];
  if (m.provincia?.nombre) sub.push(m.provincia.nombre);
  if (m.distrito?.nombre) sub.push(m.distrito.nombre);
  return args.join(" - ") + (sub.length ? ` - ${sub.join(" / ")}` : "");
}

export function StepMecanicaSuelosLiquidacion({
  methods,
  isActive,
  municipalidades,
  isLoadingMunicipalidades,
  cotizarMutation,
  quote,
  setCotizacionQuote,
  setCotizacionError,
  setCotizacionCalculating,
}: StepMecanicaSuelosLiquidacionProps) {
  const store = useMecanicaSuelosStepperStore();
  const { watch } = methods;
  const watchedMunicipalidadId = watch("municipalidad_id");
  const watchedAreaSolicitada = watch("area_solicitada");

  // Fetch tarifas vigentes específicas para MS
  const { data: tarifasVigentes, isLoading: isLoadingTarifas } = useTarifasVigentesMecanicaSuelos();

  const latestRef = useRef({ watchedMunicipalidadId, watchedAreaSolicitada });
  latestRef.current = { watchedMunicipalidadId, watchedAreaSolicitada };

  const hasValidMunicipalidad = !!watchedMunicipalidadId && watchedMunicipalidadId.length > 0;
  const hasValidArea = Number(watchedAreaSolicitada) > 0;
  const hasValidTarifas = store.selectedTarifasIds.length >= 1;
  // Cotizar solo requiere área + tarifas; municipalidad es para creación final
  const canCotizar = hasValidArea && hasValidTarifas;

  const runCotizacion = useCallback(async () => {
    const l = latestRef.current;
    if (!canCotizar) {
      notify.error("Completa los campos requeridos y selecciona al menos una tarifa antes de cotizar");
      return;
    }
    setCotizacionError(null);
    setCotizacionCalculating(true);
    try {
      const result = await cotizarMutation.mutateAsync({
        area_solicitada: Number(l.watchedAreaSolicitada),
        tarifas_ids: store.selectedTarifasIds,
      });
      setCotizacionQuote(result);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al calcular la cotización";
      setCotizacionError(msg);
      notify.error(msg);
    } finally {
      setCotizacionCalculating(false);
    }
  }, [canCotizar, cotizarMutation, setCotizacionCalculating, setCotizacionError, setCotizacionQuote, store.selectedTarifasIds]);

  // Auto-select only enabled tariff when list loads and nothing is selected yet
  useEffect(() => {
    if (
      tarifasVigentes &&
      tarifasVigentes.length > 0 &&
      store.selectedTarifasIds.length === 0
    ) {
      const enabledTarifas = tarifasVigentes.filter((t) => t.habilitada);
      if (enabledTarifas.length === 1) {
        store.setSelectedTarifasId(enabledTarifas[0].tarifa_id);
      }
    }
  }, [tarifasVigentes, store.selectedTarifasIds.length, store, store.selectedTarifasIds]);

  const handleSelectTarifa = useCallback(
    (tarifaId: string) => {
      store.setSelectedTarifasId(tarifaId);
    },
    [store],
  );

  if (!isActive) return null;

  return (
    <div className="space-y-4 min-w-0 max-w-full">
      <div className="flex flex-col md:flex-row gap-4 min-w-0">
        {/* Columna 1: Datos de Liquidación */}
        <div className="flex-1 min-w-0 rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-hidden">
          <FormSectionHeader title="Datos de Liquidación" icon={Banknote} variant="soft" />

          <div className="flex flex-col gap-4 min-w-0">
            <GenericInput
              field={{
                name: "municipalidad_id",
                label: "Municipalidad",
                type: "searchable-select",
                required: true,
                placeholder: isLoadingMunicipalidades ? "Cargando..." : "Seleccione municipalidad",
                options: (municipalidades || []).map((m) => ({
                  label: formatMunicipalidadLabel(m),
                  value: m.id,
                })),
                icon: Building2,
                isLoading: isLoadingMunicipalidades,
                labelClassName: "text-primary font-semibold",
                containerClassName: "min-w-0",
              }}
              register={methods.register as never}
              control={methods.control as never}
              errors={methods.formState.errors}
            />
          </div>

          <div className="flex flex-col gap-4 min-w-0">
            <GenericInput
              field={{
                name: "area_solicitada",
                label: "Área Solicitada (m²)",
                type: "number",
                required: true,
                placeholder: "Ej: 500",
                icon: MapPin,
                min: 0,
                step: 1,
                labelClassName: "text-primary font-semibold",
                containerClassName: "min-w-0",
              }}
              register={methods.register as never}
              control={methods.control as never}
              errors={methods.formState.errors}
            />
          </div>

          <div className="flex flex-col gap-4 min-w-0">
            <GenericInput
              field={{
                name: "expediente",
                label: "Expediente",
                type: "text",
                placeholder: "Número de expediente (opcional)",
                icon: FileText,
                labelClassName: "text-primary font-semibold",
              }}
              register={methods.register as never}
              control={methods.control as never}
              errors={methods.formState.errors}
            />
          </div>

          <GenericInput
            field={{
              name: "observacion",
              label: "Observación",
              type: "textarea",
              placeholder: "Observaciones adicionales...",
              icon: MessageSquare,
              labelClassName: "text-primary font-semibold",
            }}
            register={methods.register as never}
            control={methods.control as never}
            errors={methods.formState.errors}
          />

          {/* ── Tarifas IDs ─────────────────────────────────────────────── */}
          <TarifasSelectorMecanicaSuelos
            tarifas={tarifasVigentes ?? []}
            selectedTarifaId={store.selectedTarifasIds[0] ?? null}
            onSelect={handleSelectTarifa}
            isLoading={isLoadingTarifas}
          />
        </div>

        {/* Columna 2: Cotización */}
        <div className="flex-1 min-w-0 rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-hidden">
          <FormSectionHeader title="Cotización" icon={Calculator} variant="soft" />
          <MecanicaSuelosCotizacionDisplay quote={quote} />
          <button
            type="button"
            onClick={runCotizacion}
            disabled={!canCotizar || cotizarMutation.isPending}
            className="w-full h-10 rounded-xl font-semibold border border-border/60 hover:border-border hover:bg-background transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Calculator className="h-4 w-4" />
            {cotizarMutation.isPending ? "Calculando..." : "Calcular cotización"}
          </button>
          {!canCotizar && !cotizarMutation.isPending && (
            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              {!hasValidArea && <span>• Ingresa un área válida (mayor a 0)</span>}
              {!hasValidTarifas && <span>• Agrega al menos una tarifa</span>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Cotización Display ─────────────────────────────────────────────────────────

function MecanicaSuelosCotizacionDisplay({
  quote,
}: {
  quote: CotizacionMecanicaSuelosResponse | null;
}) {
  const formatSoles = (value: number) =>
    `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;

  if (!quote) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground italic">
        Presiona &quot;Calcular cotización&quot; para ver el resumen del cálculo.
      </div>
    );
  }

  return (
    <div className="space-y-3 border-t pt-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="text-sm font-medium">Revisión #{quote.numero_revision}</span>
        <span className="text-xs text-muted-foreground">
          UIT: S/ {quote._metadata?.uit_valor?.toFixed(2) ?? "—"}
        </span>
      </div>

      {quote.calculo_m2 && (
        <div className="space-y-2 text-sm p-3 rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Área solicitada</span>
            <span className="font-semibold text-foreground">
              {quote.calculo_m2.area_solicitada.toLocaleString("es-PE")} m²
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Derecho</span>
            <span className="font-semibold text-foreground">
              {formatSoles(quote.calculo_m2.derecho)}
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 border-t border-border pt-3">
        <div className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground text-xs">Subtotal</span>
          <span className="font-medium">{formatSoles(quote.totales.subtotal)}</span>
        </div>
        <div className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground text-xs">Total</span>
          <span className="font-medium">{formatSoles(quote.totales.total)}</span>
        </div>
        <div className="flex flex-col gap-1.5 text-base font-bold p-3 rounded-lg border border-primary bg-primary/5">
          <span className="text-primary text-xs">Total a Pagar</span>
          <span className="text-primary text-lg">{formatSoles(quote.totales.total_a_pagar)}</span>
        </div>
      </div>
    </div>
  );
}

// ── Tarifa Selector ───────────────────────────────────────────────────────────

function TarifasSelectorMecanicaSuelos({
  tarifas,
  selectedTarifaId,
  onSelect,
  isLoading,
}: {
  tarifas: Array<{
    tarifa_id: string;
    costo_por_m2: number;
    area_m2: number;
    derecho_minimo: number;
    derecho_maximo: number | null;
    habilitada: boolean;
  }>;
  selectedTarifaId: string | null;
  onSelect: (tarifaId: string) => void;
  isLoading: boolean;
}) {
  const formatSoles = (value: number) =>
    `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 min-w-0">
        <label className="text-primary font-semibold text-sm flex items-center gap-1">
          <Tag className="h-3.5 w-3.5" />
          Tarifa
          <span className="text-destructive">*</span>
        </label>
        <div className="rounded-xl border border-border bg-card p-4 animate-pulse space-y-3">
          <div className="h-4 w-40 bg-muted rounded" />
          <div className="grid grid-cols-2 gap-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-12 bg-muted rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 min-w-0">
      <label className="text-primary font-semibold text-sm flex items-center gap-1">
        <Tag className="h-3.5 w-3.5" />
        Tarifa
        <span className="text-destructive">*</span>
      </label>
      {tarifas.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          No hay tarifas vigentes disponibles
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {tarifas.map((tarifa) => {
            const isSelected = selectedTarifaId === tarifa.tarifa_id;
            const isDisabled = !tarifa.habilitada;
            return (
              <button
                key={tarifa.tarifa_id}
                type="button"
                disabled={isDisabled}
                onClick={() => !isDisabled && onSelect(tarifa.tarifa_id)}
                className={[
                  "rounded-xl border bg-card p-3 transition-all duration-200 text-left w-full flex flex-col gap-2",
                  isSelected
                    ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                    : "border-border hover:border-primary/40",
                  isDisabled && "opacity-50 cursor-not-allowed",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <span className="text-xs font-semibold text-foreground truncate">
                      {tarifa.costo_por_m2 != null ? `S/ ${tarifa.costo_por_m2.toFixed(2)}/m²` : "—"}
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5 items-end shrink-0">
                    <span className="text-[10px] text-muted-foreground">
                      Der. mín:
                    </span>
                    <span className="text-xs font-semibold text-foreground">
                      {formatSoles(tarifa.derecho_minimo)}
                    </span>
                  </div>
                </div>
                {tarifa.derecho_maximo != null && (
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">
                      Der. máx:
                    </span>
                    <span className="text-xs font-medium text-foreground">
                      {formatSoles(tarifa.derecho_maximo)}
                    </span>
                  </div>
                )}
                {isSelected && (
                  <div className="text-[10px] font-semibold text-primary pt-1 border-t border-primary/20">
                    ✓ Seleccionada
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
