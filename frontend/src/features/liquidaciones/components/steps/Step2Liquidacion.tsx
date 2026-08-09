"use client";

import {
  Banknote,
  Building2,
  Calculator,
  FileText,
  MessageSquare,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { FormSectionHeader } from "@/components-app/forms/FormSectionHeader";
import { notify } from "@/errors";
import { useCotizacionPrimeraRevision } from "../../hooks/useCotizacion";
import { useEdificacionStepperStore } from "../../store";
import type { VariablesFinancieras } from "../../types/liquidacion-edificaciones";
import type { RevisionVigente } from "../../types/revisiones-vigentes";
import { CotizacionSection } from "../CotizacionSection";
import { RevisionesVigentesTable } from "../RevisionesVigentesTable";

const TIPO_TRAMITE_OPTIONS = [
  { value: "OBRA_NUEVA", label: "Obra nueva" },
  { value: "DEMOLICION", label: "Demolición" },
  { value: "AMPLIACION", label: "Ampliación" },
  { value: "REMODELACION", label: "Remodelación" },
  { value: "MODIFICACION_LICENCIA", label: "Modificación de licencia" },
  { value: "REINTEGRO", label: "Reintegro" },
  {
    value: "PROYECTO_CON_PLANTAS_TIPICAS",
    label: "Proyecto con plantas típicas",
  },
] as const;

const PROYECTO_CON_PLANTAS_TIPICAS_TIPO = "PROYECTO_CON_PLANTAS_TIPICAS";

interface Step2LiquidacionProps {
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
  revisionesVigentes: RevisionVigente[] | undefined;
  isLoadingRevisiones: boolean;
  variablesFinancieras?: VariablesFinancieras;
  isLoadingVariables?: boolean;
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

export function Step2Liquidacion({
  methods,
  isActive,
  municipalidades,
  isLoadingMunicipalidades,
  revisionesVigentes,
  isLoadingRevisiones,
  variablesFinancieras,
  isLoadingVariables,
}: Step2LiquidacionProps) {
  const {
    selectedTarifasIds,
    setSelectedTarifasId,
    cotizacion,
    setCotizacionQuote,
    setCotizacionError,
  } = useEdificacionStepperStore();

  const { watch, setValue } = methods;
  const watchedMunicipalidadId = watch("municipalidad_id");
  const watchedTipoTramite = watch("tipo_tramite");
  const watchedValorProyecto = watch("valor_proyecto");
  const watchedValorBaseCalculo = watch("valor_base_calculo");

  const isPlantasTipicas =
    watchedTipoTramite === PROYECTO_CON_PLANTAS_TIPICAS_TIPO;

  // ── Sincronizar valor_base_calculo con valor_proyecto ────────────────────
  useEffect(() => {
    const vp = Number(watchedValorProyecto);
    const vb = Number(watchedValorBaseCalculo);
    if (vp > 0 && !isPlantasTipicas) {
      if (vb !== vp) {
        setValue("valor_base_calculo", vp as never, {
          shouldValidate: false,
          shouldDirty: false,
        });
      }
    }
  }, [
    watchedValorProyecto,
    isPlantasTipicas,
    setValue,
    watchedValorBaseCalculo,
  ]);

  // ── Selección única de tarifa (radio) ─────────────────────────────────────
  const selectedId = selectedTarifasIds[0] ?? null;

  // Auto-select si hay exactamente una tarifa habilitada y ninguna seleccionada.
  // Se re-dispara al cambiar tipo_tramite (nuevos datos filtrados).
  const hasAutoSelected = useRef(false);
  useEffect(() => {
    if (!revisionesVigentes || isLoadingRevisiones) return;
    if (selectedTarifasIds.length > 0) {
      hasAutoSelected.current = true;
      return;
    }
    if (hasAutoSelected.current) return;
    const enabled = revisionesVigentes.filter((r) => r.habilitada);
    if (enabled.length === 1) {
      setSelectedTarifasId(enabled[0].id);
      hasAutoSelected.current = true;
    }
  }, [
    revisionesVigentes,
    isLoadingRevisiones,
    selectedTarifasIds.length,
    setSelectedTarifasId,
  ]);

  // Resetear auto-select cuando cambia el tipo de trámite (nuevo filtro)
  useEffect(() => {
    hasAutoSelected.current = false;
  }, [watchedTipoTramite]);

  const handleSelectRevision = (id: string) => {
    setSelectedTarifasId(id);
  };

  // ── Cotización ──────────────────────────────────────────────────────────────
  // Backend no requiere proyecto — solo tipo_tramite, valor, valor_base y tarifas_ids.

  const cotizacionMutation = useCotizacionPrimeraRevision();

  const hasValidValorBase = Number(watchedValorBaseCalculo) > 0;
  const hasTarifa = selectedTarifasIds.length === 1;

  const valorBase =
    isPlantasTipicas &&
    watchedValorBaseCalculo &&
    Number(watchedValorBaseCalculo) > 0
      ? Number(watchedValorBaseCalculo)
      : Number(watchedValorProyecto);

  const latestRef = useRef({
    hasValidValorBase,
    hasTarifa,
    selectedTarifasIds,
    tipoTramite: watchedTipoTramite,
    valorProyecto: watchedValorProyecto,
    valorBase,
  });
  latestRef.current = {
    hasValidValorBase,
    hasTarifa,
    selectedTarifasIds,
    tipoTramite: watchedTipoTramite,
    valorProyecto: watchedValorProyecto,
    valorBase,
  };

  const runCotizacion = useCallback(async () => {
    const l = latestRef.current;
    if (!l.hasValidValorBase) {
      notify.error("Ingresa un valor de proyecto válido");
      return;
    }
    if (!l.hasTarifa || l.selectedTarifasIds.length === 0) {
      notify.error("Selecciona exactamente una revisión/tarifa");
      return;
    }
    setCotizacionError(null);
    try {
      const result = await cotizacionMutation.mutateAsync({
        tipo_tramite: l.tipoTramite as string,
        valor_proyecto: Number(l.valorProyecto),
        valor_base_calculo: l.valorBase,
        tarifas_ids: l.selectedTarifasIds,
      });
      setCotizacionQuote(result);
    } catch (e: unknown) {
      const msg =
        e instanceof Error ? e.message : "Error al calcular la cotización";
      setCotizacionError(msg);
      notify.error(msg);
    }
  }, [cotizacionMutation, setCotizacionError, setCotizacionQuote]);

  if (!isActive) return null;

  return (
    <div className="space-y-4 min-w-0 max-w-full">
      {/* ── Layout responsive: mobile = stacked, md+ = 3 columnas paralelas ──
          Mobile-first: flex-col → md:flex-row. Cada columna flex-1 para anchos iguales. */}
      <div className="flex flex-col md:flex-row gap-4 min-w-0">
        {/* ── Columna 1: Datos de Liquidación ──────────────────────────────── */}
        <div className="flex-1 min-w-0 rounded-xl border border-primary/20 bg-card p-4 space-y-4 min-w-0 overflow-hidden">
          <FormSectionHeader
            title="Datos de Liquidación"
            icon={Banknote}
            variant="soft"
          />

          <div className="flex flex-col gap-4 min-w-0">
            <GenericInput
              field={{
                name: "municipalidad_id",
                label: "Municipalidad",
                type: "searchable-select",
                required: true,
                placeholder: isLoadingMunicipalidades
                  ? "Cargando..."
                  : "Seleccione municipalidad",
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
            <GenericInput
              field={{
                name: "tipo_tramite",
                label: "Tipo de Trámite",
                type: "select",
                required: true,
                placeholder: "Seleccione tipo",
                icon: FileText,
                labelClassName: "text-primary font-semibold",
                options: [...TIPO_TRAMITE_OPTIONS],
              }}
              register={methods.register as never}
              control={methods.control as never}
              errors={methods.formState.errors}
            />
            <GenericInput
              field={{
                name: "valor_proyecto",
                label: "Valor del Proyecto (S/)",
                type: "number",
                required: true,
                placeholder: "Ej: 500000",
                icon: Banknote,
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
            {isPlantasTipicas && (
              <GenericInput
                field={{
                  name: "valor_base_calculo",
                  label: "Valor Declarado (S/)",
                  type: "number",
                  required: true,
                  placeholder: "Valor base alternativo (requerido)",
                  icon: Calculator,
                  min: 0,
                  step: 1,
                  labelClassName: "text-primary font-semibold",
                  containerClassName: "min-w-0",
                }}
                register={methods.register as never}
                control={methods.control as never}
                errors={methods.formState.errors}
              />
            )}
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
        </div>

        {/* ── Columna 2: Revisión / Tarifa ──────────────────────────────────── */}
        <div className="flex-1 min-w-0 rounded-xl border border-primary/20 bg-card p-4 space-y-4 min-w-0 overflow-hidden">
          <FormSectionHeader
            title="Revisión / Tarifa"
            icon={FileText}
            variant="soft"
          />
          <RevisionesVigentesTable
            revisiones={revisionesVigentes || []}
            selectedId={selectedId}
            onSelectRevision={handleSelectRevision}
            isLoading={isLoadingRevisiones}
          />
        </div>

        {/* ── Columna 3: Cotización ──────────────────────────────────────────── */}
        <div className="flex-1 min-w-0 rounded-xl border border-primary/20 bg-card p-4 space-y-4 min-w-0 overflow-hidden">
          <CotizacionSection
            quote={cotizacion.quote}
            isLoading={cotizacionMutation.isPending}
            onCotizar={runCotizacion}
            hasErrors={!!cotizacion.lastError}
            hasValidValorBase={hasValidValorBase}
            hasTarifa={hasTarifa}
            isLoadingData={isLoadingRevisiones || isLoadingVariables}
            variablesFinancieras={variablesFinancieras}
            isLoadingVariables={isLoadingVariables}
          />
        </div>
      </div>
    </div>
  );
}
