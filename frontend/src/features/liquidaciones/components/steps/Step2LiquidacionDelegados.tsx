"use client";

import {
  Banknote,
  Building2,
  Calculator,
  FileText,
  MessageSquare,
} from "lucide-react";
import { useEffect, useRef } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { FormSectionHeader } from "@/components-app/forms/FormSectionHeader";
import { useDelegadosVigentes } from "../../hooks/useDelegadosVigentes";
import { useLiquidacionStepperUIStore } from "../../store";
import { DelegadosSection } from "../DelegadosSection";
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

interface Step2LiquidacionDelegadosProps {
  methods: UseFormReturn<FieldValues>;
  isActive: boolean;
  // Data from parent
  municipalidades: Array<{
    id: string;
    codigo?: string | null;
    nombre: string;
    provincia?: { nombre: string } | null;
    distrito?: { nombre: string } | null;
  }>;
  isLoadingMunicipalidades: boolean;
  revisionesVigentes:
    | import("../../types/revisiones-vigentes").RevisionVigente[]
    | undefined;
  isLoadingRevisiones: boolean;
}

function formatMunicipalidadLabel(municipalidad: {
  codigo?: string | null;
  nombre: string;
  provincia?: { nombre: string } | null;
  distrito?: { nombre: string } | null;
}) {
  const codigo = municipalidad.codigo;
  const nombre = municipalidad.nombre;
  const provincia = municipalidad.provincia?.nombre;
  const distrito = municipalidad.distrito?.nombre;

  let label = codigo ? `${codigo} - ${nombre}` : nombre;

  if (provincia && distrito) {
    label += ` - ${provincia} / ${distrito}`;
  } else if (provincia) {
    label += ` - ${provincia}`;
  } else if (distrito) {
    label += ` - ${distrito}`;
  }

  return label;
}

export function Step2LiquidacionDelegados({
  methods,
  isActive,
  municipalidades,
  isLoadingMunicipalidades,
  revisionesVigentes,
  isLoadingRevisiones,
}: Step2LiquidacionDelegadosProps) {
  const {
    selectedDelegados,
    toggleDelegado,
    selectedRevisionIds,
    lockedRevisionIds,
  } = useLiquidacionStepperUIStore();

  const { watch, setValue } = methods;
  const watchedMunicipalidadId = watch("municipalidad_id");
  const watchedTipoTramite = watch("tipo_tramite");
  // Watched but intentionally unused — cotizacion auto-calculates from RHF values
  const _watchedValorProyecto = watch("valor_proyecto");

  const isPlantasTipicas =
    watchedTipoTramite === PROYECTO_CON_PLANTAS_TIPICAS_TIPO;

  // Delegate filtering: use first selected revision if exactly one is selected
  const singleRevisionId =
    selectedRevisionIds.length === 1 ? selectedRevisionIds[0] : null;

  const { data: delegadosVigentes, isLoading: isLoadingDelegados } =
    useDelegadosVigentes(watchedMunicipalidadId || null, singleRevisionId);

  // Auto-select all habilitadas revisiones when data first loads (once)
  const hasInitializedRevisiones = useRef(false);
  useEffect(() => {
    if (
      !isLoadingRevisiones &&
      revisionesVigentes &&
      !hasInitializedRevisiones.current
    ) {
      hasInitializedRevisiones.current = true;
      const habilesIds = revisionesVigentes
        .filter((rev) => rev.habilitada)
        .map((rev) => rev.id);
      setValue("revisiones_ids", habilesIds as never, {
        shouldValidate: false,
        shouldDirty: true,
      });
      // Also update the store
      useLiquidacionStepperUIStore.getState().setLockedRevisionIds(habilesIds);
      useLiquidacionStepperUIStore
        .getState()
        .setSelectedRevisionIds(habilesIds);
    }
  }, [isLoadingRevisiones, revisionesVigentes, setValue]);

  // Also sync selectedRevisionIds to store on changes
  const handleRevisionToggle = (id: string) => {
    const updated = selectedRevisionIds.includes(id)
      ? selectedRevisionIds.filter((r) => r !== id)
      : [...selectedRevisionIds, id];
    useLiquidacionStepperUIStore.getState().setSelectedRevisionIds(updated);
  };

  if (!isActive) return null;

  return (
    <div className="space-y-0 min-w-0 max-w-full">
      {/* ── Sections flow responsively: grid-auto-fill adapts columns to available space ─── */}
      <div className="grid grid-auto-fill-md gap-4 min-w-0">
        {/* ── Liquidación Datos ─────────────────────────────── */}
        <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 min-w-0 overflow-hidden">
          <FormSectionHeader
            title="Datos de Liquidación"
            icon={Banknote}
            variant="soft"
          />

          {/* Row 1: Municipalidad + Tipo Trámite + Valor Proyecto */}
          <div className="grid grid-auto-fill-sm gap-4 min-w-0">
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
                labelClassName: "text-primary font-semibold",
              }}
              register={methods.register as never}
              control={methods.control as never}
              errors={methods.formState.errors}
            />
          </div>

          {/* Row 2: Expediente + Valor Base (plantas típicas only) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 min-w-0">
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
                  labelClassName: "text-primary font-semibold",
                }}
                register={methods.register as never}
                control={methods.control as never}
                errors={methods.formState.errors}
              />
            )}
          </div>

          {/* Observación */}
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

        {/* ── Delegados (OPCIONAL - ya no se envía en creación) ── */}
        {/* TODO: En una fase posterior se implementará endpoint separado para asignar delegados */}
        <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 min-w-0 overflow-hidden opacity-60">
          <FormSectionHeader
            title="Delegados (Opcional)"
            icon={FileText}
            variant="soft"
          />
          <p className="text-xs text-muted-foreground italic">
            La asignación de delegados se hará por endpoint separado
          </p>
          <DelegadosSection
            delegados={delegadosVigentes || []}
            selectedIds={selectedDelegados}
            isLoading={isLoadingDelegados}
            hasMunicipalidad={!!watchedMunicipalidadId}
            onToggleDelegado={(id) => {
              toggleDelegado(id);
            }}
          />
        </div>

        {/* ── Revisiones / Especialidades ────────────────────── */}
        {/* TODO: Para esta fase, solo se permite seleccionar UNA revisión/tarifa */}
        <div className="rounded-xl border border-primary/20 bg-card p-4 space-y-4 min-w-0 overflow-hidden">
          <FormSectionHeader
            title="Revisión / Tarifa"
            icon={FileText}
            variant="soft"
            count={selectedRevisionIds.length}
            countLabel="seleccionada"
          />
          <p className="text-xs text-muted-foreground">
            Seleccione exactamente una revisión para esta fase
          </p>

          <RevisionesVigentesTable
            revisiones={revisionesVigentes || []}
            selectedId={selectedRevisionIds[0] ?? null}
            onSelectRevision={(id) =>
              useLiquidacionStepperUIStore.getState().setSelectedRevisionIds([id])
            }
            isLoading={isLoadingRevisiones}
            lockedIds={lockedRevisionIds}
          />
        </div>
      </div>
    </div>
  );
}
