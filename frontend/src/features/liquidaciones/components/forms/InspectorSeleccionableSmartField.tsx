"use client";

import { BadgeCheck, HardHat, Loader2, User } from "lucide-react";
/**
 * InspectorSeleccionableSmartField — Smart Field para elegir el inspector
 * de una liquidación de Inspección de Obra (form de creación).
 *
 * BAJO DEMANDA pero sin botón manual:
 * - Lee la categoría del form con `methods.watch("categoria")` (ya seleccionada
 *   en el smart field de tarifas).
 * - Cuando hay tipo_liquidacion (de la previa) Y categoría, consulta
 *   GET /liquidaciones/inspectores/seleccionables?tipo_liquidacion=&categoria=
 *   automáticamente.
 * - Muestra los inspectores de esa categoría para elegir (single-select).
 * - `inspector_id` se setea en react-hook-form.
 */
import { useCallback, useEffect, useMemo } from "react";
import type { UseFormReturn } from "react-hook-form";
import type { InspectorVigente } from "@/features/inspectores/types/inspectores.types";
import { useInspectoresVigentes } from "../../hooks/useInspectoresVigentes";
import type { NuevaRevisionInspeccionObraFormData } from "../../schemas/liquidacion-nueva-revision-io.schema";

interface InspectorSeleccionableSmartFieldProps {
  methods: UseFormReturn<NuevaRevisionInspeccionObraFormData>;
  /** Tipo de liquidación de la previa (EDIFICACION o HABILITACION_URBANA). null si no hay previa */
  tipoLiquidacion?: string | null;
}

export function InspectorSeleccionableSmartField({
  methods,
  tipoLiquidacion,
}: InspectorSeleccionableSmartFieldProps) {
  // Categoría ya seleccionada en el form (smart field de tarifas) — la observamos con watch
  const categoria = methods.watch("categoria");

  // Inspector seleccionado en RHF
  const inspectorId = methods.watch("inspector_id");

  // Consulta automática: enabled cuando hay tipo + categoría
  const canFetch = !!tipoLiquidacion && !!categoria;

  const { data: inspectores = [], isLoading } = useInspectoresVigentes(
    tipoLiquidacion,
    categoria || null,
    undefined,
    canFetch,
  );

  const inspectorSeleccionado = useMemo<InspectorVigente | null>(() => {
    if (!inspectorId) return null;
    return inspectores.find((i) => i.id === inspectorId) ?? null;
  }, [inspectorId, inspectores]);

  const handleSelect = useCallback(
    (id: string) => {
      methods.setValue("inspector_id", id, {
        shouldValidate: true,
        shouldDirty: true,
      });
    },
    [methods],
  );

  // Limpiar inspector si ya no está en la lista de la categoría
  useEffect(() => {
    if (inspectorId && inspectores.length > 0) {
      const sigue = inspectores.some((i) => i.id === inspectorId);
      if (!sigue) {
        methods.setValue("inspector_id", "", {
          shouldValidate: true,
        });
      }
    }
  }, [inspectorId, inspectores, methods]);

  return (
    <div className="space-y-3">
      {/* ── Estados ── */}
      {!tipoLiquidacion && (
        <p className="text-xs text-muted-foreground">
          Selecciona una liquidación previa para buscar inspectores.
        </p>
      )}

      {tipoLiquidacion && !categoria && (
        <p className="text-xs text-muted-foreground">
          Selecciona una categoría para cargar los inspectores disponibles.
        </p>
      )}

      {canFetch && isLoading && (
        <div className="flex items-center gap-2 py-2">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">
            Cargando inspectores de la categoría {categoria}...
          </span>
        </div>
      )}

      {canFetch && !isLoading && inspectores.length === 0 && (
        <p className="text-xs text-muted-foreground">
          No hay inspectores vigentes para la categoría {categoria} en este tipo
          de liquidación.
        </p>
      )}

      {/* ── Lista de resultados (tarjetas seleccionables) ── */}
      {canFetch && !isLoading && inspectores.length > 0 && (
        <div className="grid grid-cols-1 gap-2 max-h-64 overflow-y-auto pr-1">
          {inspectores.map((inspector) => {
            const isSelected = inspector.id === inspectorId;
            return (
              <button
                key={inspector.id}
                type="button"
                onClick={() => handleSelect(inspector.id)}
                className={[
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all text-left",
                  isSelected
                    ? "bg-primary/10 border-primary/60 ring-2 ring-primary/30"
                    : "bg-card border-border/70 hover:border-primary/40",
                ].join(" ")}
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-muted/80 text-muted-foreground">
                  <HardHat className="h-4 w-4" />
                </div>
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="text-sm font-bold text-foreground truncate">
                    {inspector.nombre_completo}
                  </span>
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground mt-0.5">
                    <span className="inline-flex items-center gap-1">
                      <User className="h-3 w-3" /> CIP {inspector.cip}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <BadgeCheck className="h-3 w-3" />{" "}
                      {inspector.numero_registro}
                    </span>
                    {inspector.especialidad && (
                      <span className="rounded bg-primary/10 px-1.5 py-0.5 text-primary">
                        {inspector.especialidad.nombre}
                      </span>
                    )}
                  </div>
                </div>
                <span
                  className={[
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                    isSelected ? "border-primary" : "border-border",
                  ].join(" ")}
                >
                  {isSelected && (
                    <span className="h-2 w-2 rounded-full bg-primary" />
                  )}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* ── Inspector seleccionado (feedback) ── */}
      {inspectorId && inspectorSeleccionado && (
        <p className="text-xs text-green-600 dark:text-green-400">
          Inspector asignado: {inspectorSeleccionado.nombre_completo}
        </p>
      )}
    </div>
  );
}
