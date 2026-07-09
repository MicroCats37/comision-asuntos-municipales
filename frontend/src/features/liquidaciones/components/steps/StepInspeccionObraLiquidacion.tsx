/**
 * Step: Liquidación Inspección de Obra — visitas + categoría + campos comunes + cotización + tarifas.
 */
"use client";

import { Banknote, Building2, Calculator, FileText, MessageSquare, Tag } from "lucide-react";
import { useCallback, useEffect, useRef } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { FormSectionHeader } from "@/components-app/forms/FormSectionHeader";
import { notify } from "@/errors";
import { useInspeccionObraStepperStore } from "../../store";
import { CATEGORIAS_IO } from "../../types/liquidacion-inspeccion-obra.types";
import type { CotizacionIOResponse } from "../../types/liquidacion-inspeccion-obra.types";
import { useTarifasVigentesInspeccionObra } from "../../hooks/useTarifasVigentes";

const CATEGORIA_OPTIONS = CATEGORIAS_IO.map((c) => ({
  value: c,
  label: `Categoría ${c}`,
}));

interface StepInspeccionObraLiquidacionProps {
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
      payload: {
        cantidad_visitas: number;
        categoria: "C1" | "C2" | "C3" | "C4";
        municipalidad_id: string;
        tarifas_ids: string[];
      },
    ) => Promise<CotizacionIOResponse>;
    isPending: boolean;
  };
  quote: CotizacionIOResponse | null;
  setCotizacionQuote: (quote: CotizacionIOResponse | null) => void;
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

export function StepInspeccionObraLiquidacion({
  methods,
  isActive,
  municipalidades,
  isLoadingMunicipalidades,
  cotizarMutation,
  quote,
  setCotizacionQuote,
  setCotizacionError,
  setCotizacionCalculating,
}: StepInspeccionObraLiquidacionProps) {
  const store = useInspeccionObraStepperStore();
  const { watch } = methods;
  const watchedMunicipalidadId = watch("municipalidad_id");
  const watchedCantidadVisitas = watch("cantidad_visitas");
  const watchedCategoria = watch("categoria");

  // Fetch tarifas vigentes from the new endpoint, filtered by category
  const { data: tarifasVigentes, isLoading: isLoadingTarifas } = useTarifasVigentesInspeccionObra({
    categoria: watchedCategoria,
  });

  const latestRef = useRef({ watchedMunicipalidadId, watchedCantidadVisitas, watchedCategoria });
  latestRef.current = { watchedMunicipalidadId, watchedCantidadVisitas, watchedCategoria };

  const hasValidMunicipalidad = !!watchedMunicipalidadId && watchedMunicipalidadId.length > 0;
  const hasValidVisitas = Number(watchedCantidadVisitas) >= 1;
  const hasValidCategoria = !!watchedCategoria && watchedCategoria.length > 0;
  const hasValidTarifas = store.selectedTarifasIds.length >= 1;
  const canCotizar = hasValidMunicipalidad && hasValidVisitas && hasValidCategoria && hasValidTarifas;

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
        cantidad_visitas: Number(l.watchedCantidadVisitas),
        categoria: l.watchedCategoria as "C1" | "C2" | "C3" | "C4",
        municipalidad_id: l.watchedMunicipalidadId as string,
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

  // Auto-select唯一 enabled tariff when list loads and nothing is selected yet
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

  // Reset selected tariff when category changes (tariffs are category-specific)
  useEffect(() => {
    if (watchedCategoria && tarifasVigentes) {
      const selectedId = store.selectedTarifasIds[0];
      if (selectedId) {
        const isStillValid = tarifasVigentes.some(
          (t) => t.tarifa_id === selectedId && t.categoria === watchedCategoria,
        );
        if (!isStillValid) {
          store.setSelectedTarifasIds([]);
        }
      }
    }
  }, [watchedCategoria, tarifasVigentes, store]);

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
                name: "cantidad_visitas",
                label: "Cantidad de Visitas",
                type: "number",
                required: true,
                placeholder: "Ej: 3",
                icon: Calculator,
                min: 1,
                step: 1,
                labelClassName: "text-primary font-semibold",
                containerClassName: "min-w-0",
              }}
              register={methods.register as never}
              control={methods.control as never}
              errors={methods.formState.errors}
            />
            <GenericInput
              field={{
                name: "categoria",
                label: "Categoría",
                type: "select",
                required: true,
                placeholder: "Seleccione categoría",
                icon: FileText,
                labelClassName: "text-primary font-semibold",
                options: CATEGORIA_OPTIONS,
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
          <TarifasSelectorInspeccion
            tarifas={tarifasVigentes ?? []}
            selectedTarifaId={store.selectedTarifasIds[0] ?? null}
            onSelect={handleSelectTarifa}
            isLoading={isLoadingTarifas}
          />
        </div>

        {/* Columna 2: Cotización */}
        <div className="flex-1 min-w-0 rounded-xl border border-primary/20 bg-card p-4 space-y-4 overflow-hidden">
          <FormSectionHeader title="Cotización" icon={Calculator} variant="soft" />
          <IOCotizacionDisplay quote={quote} />
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
              {!hasValidMunicipalidad && <span>• Selecciona una municipalidad</span>}
              {!hasValidVisitas && <span>• Ingresa un número de visitas válido (mínimo 1)</span>}
              {!hasValidCategoria && <span>• Selecciona una categoría</span>}
              {!hasValidTarifas && <span>• Agrega al menos una tarifa</span>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Tarifa Selector (reemplaza input manual UUID) ──────────────────────────────

function TarifasSelectorInspeccion({
  tarifas,
  selectedTarifaId,
  onSelect,
  isLoading,
}: {
  tarifas: Array<{
    tarifa_id: string;
    detalle_id: string;
    costo_por_visita: number;
    visitas_minimas: number;
    categoria: string;
    habilitada: boolean;
  }>;
  selectedTarifaId: string | null;
  onSelect: (tarifaId: string) => void;
  isLoading: boolean;
}) {
  const formatSoles = (value: number) =>
    `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;

  function getCategoriaLabel(categoria: string) {
    switch (categoria) {
      case "C1":
        return "Categoría C1";
      case "C2":
        return "Categoría C2";
      case "C3":
        return "Categoría C3";
      case "C4":
        return "Categoría C4";
      default:
        return categoria;
    }
  }

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
                    <span className="text-xs font-semibold text-foreground">
                      {getCategoriaLabel(tarifa.categoria)}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {tarifa.visitas_minimas} visita(s) mín.
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5 items-end shrink-0">
                    <span className="text-[10px] text-muted-foreground">
                      Costo/visita:
                    </span>
                    <span className="text-xs font-semibold text-foreground">
                      {formatSoles(tarifa.costo_por_visita)}
                    </span>
                  </div>
                </div>
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

// ── Cotización Display ──

function IOCotizacionDisplay({
  quote,
}: {
  quote: CotizacionIOResponse | null;
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
          UIT: S/ {quote._metadata.uit_valor.toFixed(2)}
        </span>
      </div>

      {quote.calculo_visitas && (
        <div className="space-y-2 text-sm p-3 rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Cant. Visitas</span>
            <span className="font-semibold text-foreground">
              {quote.calculo_visitas.cantidad_visitas}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Visitas base cálculo</span>
            <span className="font-semibold text-foreground">
              {quote.calculo_visitas.visitas_base_calculo}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Derecho</span>
            <span className="font-semibold text-foreground">
              {formatSoles(quote.calculo_visitas.derecho)}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Categoría</span>
            <span className="font-semibold text-foreground">
              {quote.calculo_visitas.categoria}
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
          <span className="text-muted-foreground text-xs">IGV ({quote._metadata.igv_valor * 100}%)</span>
          <span className="font-medium">{formatSoles(quote.totales.igv)}</span>
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
