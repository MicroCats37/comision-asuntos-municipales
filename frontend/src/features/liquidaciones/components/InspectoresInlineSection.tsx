"use client";

import { Plus, UserCheck, X } from "lucide-react";
import type { InspectorVigente } from "../types/liquidacion-general";

interface InspectoresInlineSectionProps {
  /** Currently selected inspector objects */
  inspectores: InspectorVigente[];
  /** Whether the section is read-only */
  readOnly?: boolean;
  /** Callback when user clicks add button */
  onAddInspector: () => void;
  /** Callback when user clicks remove on an inspector */
  onRemoveInspector: (id: string) => void;
}

/**
 * Reusable Inspectores section for IO forms.
 * Displays selected inspectors as chips and supports add/remove when not readOnly.
 */
export function InspectoresInlineSection({
  inspectores,
  readOnly = false,
  onAddInspector,
  onRemoveInspector,
}: InspectoresInlineSectionProps) {
  const count = inspectores.length;

  return (
    <div className="space-y-2.5">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border/40 pb-2 text-primary">
        <UserCheck className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
          Inspectores
        </h3>
        {count > 0 && (
          <span className="text-[10px] font-medium text-muted-foreground">
            ({count} inspector{count !== 1 ? "es" : ""})
          </span>
        )}
        {!readOnly && (
          <button
            type="button"
            onClick={onAddInspector}
            className="ml-auto inline-flex items-center gap-1.5 rounded-md border border-primary/25 bg-primary/5 px-2.5 py-1 text-xs font-medium text-primary transition-colors hover:border-primary/40 hover:bg-primary/10"
            aria-label="Agregar inspector"
          >
            <Plus className="h-3.5 w-3.5" />
            Agregar inspector
          </button>
        )}
      </div>

      {/* Content */}
      {count > 0 ? (
        <div className="flex flex-wrap gap-2">
          {inspectores.map((inspector) => (
            <div
              key={inspector.id}
              className="inline-flex max-w-full items-center gap-2 rounded-full border border-border/70 bg-secondary/30 px-2.5 py-1.5 transition-colors hover:border-primary/35 hover:bg-secondary/60"
            >
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <UserCheck className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0 text-xs leading-tight">
                <div className="flex max-w-[260px] items-center gap-1.5 sm:max-w-[360px]">
                  <span className="truncate font-semibold text-foreground">
                    {inspector.nombre_completo}
                  </span>
                </div>
                <div className="flex max-w-[260px] items-center gap-1.5 truncate text-[11px] text-muted-foreground sm:max-w-[360px]">
                  <span className="shrink-0">CIP: {inspector.cip}</span>
                  {inspector.numero_registro && (
                    <span className="shrink-0">• Reg. {inspector.numero_registro}</span>
                  )}
                  {inspector.especialidad && (
                    <span className="shrink-0">• {inspector.especialidad.nombre}</span>
                  )}
                </div>
              </div>
              {!readOnly && (
                <button
                  type="button"
                  onClick={() => onRemoveInspector(inspector.id)}
                  className="ml-0.5 rounded-full p-1 transition-colors hover:bg-destructive/10"
                  aria-label={`Remover inspector ${inspector.nombre_completo}`}
                >
                  <X className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          {readOnly
            ? "Sin inspectores registrados."
            : "Agrega inspectores para esta inspección de obra."}
        </p>
      )}
    </div>
  );
}
