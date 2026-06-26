"use client";

import { User, Plus, X, HardHat } from "lucide-react";
import type { ProyectistaInline } from "../types/proyectista";

/**
 * Base proyectista type with required cip for identification.
 * Used as common identifier across different proyectista representations.
 */
type BaseProyectista = {
  cip?: string | null;
  nombres?: string;
  apellidos?: string;
};

interface ProyectistaSectionProps<T extends BaseProyectista = ProyectistaInline> {
  /** List of currently selected proyectistas */
  selectedProyectistas: T[];
  /** Whether the section is read-only (no add/remove) */
  readOnly?: boolean;
  /** Callback when user clicks add button */
  onAddProyectista: () => void;
  /** Callback when user clicks remove on a proyectista (uses cip) */
  onRemoveProyectista: (cip: string) => void;
  /** Optional map of especialidad_id to label for display */
  especialidadLabels?: Record<string, string>;
}

/**
 * Reusable Proyectistas section for forms.
 * Displays selected proyectistas as cards and supports add/remove when not readOnly.
 */
export function ProyectistasSection<T extends BaseProyectista = ProyectistaInline>({
  selectedProyectistas,
  readOnly = false,
  onAddProyectista,
  onRemoveProyectista,
  especialidadLabels = {},
}: ProyectistaSectionProps<T>) {
  const count = selectedProyectistas.length;

  return (
    <div className="space-y-4">
      {/* Header - aligned with DelegadosSection/CotizacionSection style */}
      <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
        <User className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide">
          Proyectistas
        </h3>
        {count > 0 && (
          <span className="ml-auto text-[10px] font-medium opacity-75">
            ({count} seleccionado{count !== 1 ? "s" : ""})
          </span>
        )}
      </div>

      {/* Content */}
      {count > 0 ? (
        <div className="flex flex-col gap-2">
          {/* Proyectista cards - full width vertical stack */}
          {selectedProyectistas.map((proyectista) => {
            const cip = proyectista.cip ?? "unknown";
            const nombreCompleto =
              proyectista.nombres && proyectista.apellidos
                ? `${proyectista.nombres} ${proyectista.apellidos}`
                : cip !== "unknown"
                  ? `CIP: ${cip}`
                  : "Sin CIP";

            return (
              <div
                key={cip}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border bg-secondary/30 border-border/70 hover:bg-secondary/60 hover:border-primary/40 hover:shadow-sm hover:shadow-primary/10 transition-all"
              >
                {/* Avatar badge with primary accent ring */}
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/20">
                  <HardHat className="h-5 w-5" />
                </div>
                <div className="flex flex-col min-w-0 flex-1">
                  {/* Name - primary emphasis */}
                  <span className="text-sm font-bold text-foreground truncate">
                    {nombreCompleto}
                  </span>
                  {/* Metadata row - subtle with accent dots, responsive wrapping */}
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground mt-1">
                    {cip !== "unknown" && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded bg-muted/70 text-foreground/80 font-medium whitespace-nowrap">
                        CIP {cip}
                      </span>
                    )}
                    {"especialidad_id" in proyectista && (proyectista as { especialidad_id?: string }).especialidad_id && (
                      <>
                        <span className="text-muted-foreground/50">•</span>
                        <span className="whitespace-nowrap truncate max-w-[150px] sm:max-w-[200px]" title={especialidadLabels[(proyectista as { especialidad_id: string }).especialidad_id] ||
                            (proyectista as { especialidad_id: string }).especialidad_id}>
                          {especialidadLabels[(proyectista as { especialidad_id: string }).especialidad_id] ||
                            (proyectista as { especialidad_id: string }).especialidad_id}
                        </span>
                      </>
                    )}
                    {"descripcion" in proyectista && (proyectista as { descripcion?: string }).descripcion && (
                      <>
                        <span className="text-muted-foreground/50">•</span>
                        <span title={(proyectista as { descripcion: string }).descripcion} className="whitespace-nowrap truncate max-w-[120px] sm:max-w-[180px]">
                          {(proyectista as { descripcion: string }).descripcion.length > 12
                            ? `${(proyectista as { descripcion: string }).descripcion.slice(0, 12)}...`
                            : (proyectista as { descripcion: string }).descripcion}
                        </span>
                      </>
                    )}
                  </div>
                </div>
                {!readOnly && (
                  <button
                    type="button"
                    onClick={() => cip !== "unknown" && onRemoveProyectista(cip)}
                    className="ml-1 hover:bg-destructive/10 rounded p-1 transition-colors shrink-0"
                    aria-label={`Remover ${nombreCompleto}`}
                  >
                    <X className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                  </button>
                )}
              </div>
            );
          })}

          {/* Add tile - full width, shown after proyectistas */}
          {!readOnly && (
            <button
              type="button"
              onClick={onAddProyectista}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-border hover:border-primary/40 hover:bg-secondary/30 transition-all text-muted-foreground hover:text-foreground"
              aria-label="Agregar proyectista"
            >
              <Plus className="h-4 w-4" />
              <span className="text-sm font-medium">Agregar proyectista</span>
            </button>
          )}
        </div>
      ) : (
        /* Empty state - centered add card, similar to image upload UI */
        <button
          type="button"
          onClick={onAddProyectista}
          disabled={readOnly}
          className={`
            w-full flex flex-col items-center justify-center gap-3 p-8 rounded-xl border border-dashed transition-all
            ${readOnly
              ? "border-border bg-muted/30 cursor-not-allowed"
              : "border-border hover:border-primary/40 hover:bg-secondary/30 cursor-pointer"
            }
          `}
          aria-label="Agregar proyectista"
        >
          <div className={`
            flex h-12 w-12 items-center justify-center rounded-full
            ${readOnly ? "bg-muted" : "bg-primary/10"}
          `}>
            <Plus className={`h-6 w-6 ${readOnly ? "text-muted-foreground" : "text-primary"}`} />
          </div>
          <div className="text-center">
            <p className={`text-sm font-medium ${readOnly ? "text-muted-foreground" : "text-foreground"}`}>
              {readOnly ? "Sin proyectistas" : "Agregar proyectista"}
            </p>
            {!readOnly && (
              <p className="text-xs text-muted-foreground mt-1">
                Busca y agrega un ingeniero habilitado
              </p>
            )}
          </div>
        </button>
      )}
    </div>
  );
}
