"use client";

import { Briefcase, Loader2 } from "lucide-react";
import { useCallback } from "react";
import { useInspectorOperatividades } from "@/features/finanzas/hooks/useInspectorOperatividades";
import type { InspectorOperacion } from "@/features/finanzas/schemas/rh-inspector-mensual.schema";

interface InspectorOperacionSmartFieldProps {
  cip: string;
  vigente?: boolean;
  onSelect: (operacion: InspectorOperacion | null) => void;
  selectedId?: string | null;
  disabled?: boolean;
}

/** Selector de operatividad usado exclusivamente por el flujo RH de inspector. */
export function InspectorOperacionSmartField({
  cip,
  vigente,
  onSelect,
  selectedId,
  disabled = false,
}: InspectorOperacionSmartFieldProps) {
  const {
    data: operatividades = [],
    isLoading,
    isError,
  } = useInspectorOperatividades({
    cip,
    vigente,
    enabled: cip.length === 6,
  });

  const handleSelect = useCallback(
    (operacion: InspectorOperacion) => onSelect(operacion),
    [onSelect],
  );

  if (!cip.trim()) {
    return (
      <p className="text-xs text-muted-foreground">
        Ingresa el CIP del inspector para cargar sus operatividades.
      </p>
    );
  }

  if (cip.trim().length < 6) {
    return (
      <p className="text-xs text-muted-foreground">
        Ingresa los 6 dígitos del CIP del inspector.
      </p>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-3 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Buscando operatividades...
      </div>
    );
  }

  if (isError) {
    return (
      <p className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
        No se pudieron cargar las operatividades. Verifica el CIP e intenta
        nuevamente.
      </p>
    );
  }

  if (operatividades.length === 0) {
    return (
      <p className="rounded-lg border border-border bg-muted/20 p-3 text-xs text-muted-foreground">
        No hay operatividades para el CIP{" "}
        <span className="font-semibold">{cip}</span> con la vigencia
        seleccionada.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Selecciona la operatividad que corresponde al RH.
      </p>
      <div className="grid grid-cols-1 gap-2 max-h-72 overflow-y-auto pr-1">
        {operatividades.map((operacion) => (
          <button
            key={operacion.inspector_operacion_id}
            type="button"
            disabled={disabled}
            onClick={() => handleSelect(operacion)}
            className={`flex w-full items-start gap-3 rounded-xl border px-3 py-3 text-left transition-all ${operacion.inspector_operacion_id === selectedId ? "border-primary bg-primary/10 ring-2 ring-primary/30" : "border-border/70 bg-card hover:border-primary/40"} ${disabled ? "cursor-not-allowed opacity-50" : ""}`}
          >
            <Briefcase className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-bold">
                {operacion.tipo_liquidacion}
              </span>
              <span className="block text-xs text-muted-foreground">
                {operacion.especialidad?.nombre ?? "Sin especialidad"} ·
                Registro {operacion.numero_registro}
              </span>
              <span className="block text-[10px] text-muted-foreground/70">
                {operacion.periodo_inicio ?? "Sin inicio"}{" "}
                {operacion.periodo_fin
                  ? `a ${operacion.periodo_fin}`
                  : "sin fecha fin"}
              </span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
