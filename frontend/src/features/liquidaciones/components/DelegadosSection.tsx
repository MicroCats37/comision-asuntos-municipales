"use client";

import { Users, Loader2 } from "lucide-react";
import type { DelegadoVigente } from "../types/liquidacion-edificaciones";

interface DelegadosSectionProps {
  /** List of available delegates for the selected municipalidad */
  delegados: DelegadoVigente[];
  /** Currently selected delegate IDs */
  selectedIds: string[];
  /** Whether delegates are being loaded */
  isLoading?: boolean;
  /** Whether a municipalidad has been selected */
  hasMunicipalidad: boolean;
  /** Callback when user toggles a delegate */
  onToggleDelegado: (id: string) => void;
}

/**
 * Delegados section for liquidacion form.
 * Shows available delegates for the selected municipalidad and allows multi-select.
 * Delegates are grouped by specialty (especialidad.nombre).
 */
export function DelegadosSection({
  delegados,
  selectedIds,
  isLoading = false,
  hasMunicipalidad,
  onToggleDelegado,
}: DelegadosSectionProps) {
  // No municipalidad selected yet
  if (!hasMunicipalidad) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
          <Users className="h-4 w-4" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            Delegados
          </h3>
        </div>
        <p className="text-sm text-muted-foreground italic py-2">
          Seleccione una municipalidad para ver los delegados disponibles
        </p>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
          <Users className="h-4 w-4" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            Delegados
          </h3>
        </div>
        <div className="flex items-center gap-2 py-2">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Cargando delegados...</span>
        </div>
      </div>
    );
  }

  // No delegates available
  if (delegados.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
          <Users className="h-4 w-4" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            Delegados
          </h3>
        </div>
        <p className="text-sm text-muted-foreground italic py-2">
          No hay delegados vigentes para esta municipalidad
        </p>
      </div>
    );
  }

  // Group delegates by specialty
  const groupedByEspecialidad = delegados.reduce<Record<string, DelegadoVigente[]>>((acc, delegado) => {
    const specialtyName = delegado.especialidad.nombre;
    if (!acc[specialtyName]) {
      acc[specialtyName] = [];
    }
    acc[specialtyName].push(delegado);
    return acc;
  }, {});

  // Sort specialties alphabetically
  const sortedSpecialties = Object.keys(groupedByEspecialidad).sort((a, b) =>
    a.localeCompare(b, undefined, { sensitivity: "base" })
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
        <Users className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide">
          Delegados
        </h3>
        <span className="ml-auto text-[10px] font-medium opacity-75">
          ({selectedIds.length} seleccionado{selectedIds.length !== 1 ? "s" : ""})
        </span>
      </div>

      {/* Grouped Delegates */}
      <div className="space-y-6">
        {sortedSpecialties.map((specialtyName) => {
          const specialtyDelegados = groupedByEspecialidad[specialtyName];
          return (
            <div key={specialtyName} className="space-y-3">
              {/* Specialty Group Header */}
              <div className="flex items-center gap-2">
                <div className="h-px flex-1 bg-border/60" />
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground shrink-0">
                  {specialtyName}
                </span>
                <div className="h-px flex-1 bg-border/60" />
              </div>

              {/* Delegates in this specialty */}
              <div className="flex flex-col gap-2 w-full">
                {specialtyDelegados.map((delegado) => {
                  const isSelected = selectedIds.includes(delegado.id);
                  return (
                      <button
                      key={delegado.id}
                      type="button"
                      onClick={() => onToggleDelegado(delegado.id)}
                      className={`
                        w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl border transition-all text-left
                        ${isSelected
                          ? "bg-primary/10 border-primary/60 ring-2 ring-primary/30 hover:bg-primary/15 hover:border-primary/80 shadow-sm shadow-primary/15"
                          : "bg-secondary/30 border-border/70 hover:bg-secondary/60 hover:border-primary/40 hover:shadow-sm hover:shadow-primary/10"
                        }
                      `}
                    >
                      <div className="flex items-center gap-3">
                        {/* Avatar with selected accent ring */}
                        <div className={`
                          flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition-all
                          ${isSelected ? "bg-primary text-primary-foreground shadow-sm shadow-primary/25 ring-2 ring-primary/40" : "bg-muted/80 text-muted-foreground"}
                        `}>
                          <Users className={`h-4 w-4 ${isSelected ? "" : ""}`} />
                        </div>
                        <div className="flex flex-col">
                          {/* Name - bold for emphasis */}
                          <span className={`text-sm font-bold ${isSelected ? "text-foreground" : "text-foreground/90"}`}>
                            {delegado.nombre_completo}
                          </span>
                          {/* Metadata - subtle with badges, responsive wrapping */}
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground mt-1">
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-muted/70 text-foreground/80 font-medium whitespace-nowrap">
                              CIP {delegado.cip}
                            </span>
                            <span className="text-muted-foreground/50">•</span>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded capitalize whitespace-nowrap ${isSelected ? "bg-primary/20 text-primary" : "bg-secondary/70 text-muted-foreground/80"}`}>
                              {delegado.tipo}
                            </span>
                          </div>
                        </div>
                      </div>
                      {isSelected && (
                        <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center shrink-0 shadow-sm shadow-primary/30">
                          <svg className="h-2.5 w-2.5 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
