"use client";

import { User, Plus, X, HardHat } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ProyectistaResult } from "../types/proyectista";

interface ProyectistaSectionProps {
  /** List of currently selected proyectistas */
  selectedProyectistas: ProyectistaResult[];
  /** Whether the section is read-only (no add/remove) */
  readOnly?: boolean;
  /** Callback when user clicks add button */
  onAddProyectista: () => void;
  /** Callback when user clicks remove on a proyectista */
  onRemoveProyectista: (proyectistaId: string) => void;
}

/**
 * Reusable Proyectistas section for forms.
 * Displays selected proyectistas as cards/chips and supports add/remove when not readOnly.
 */
export function ProyectistasSection({
  selectedProyectistas,
  readOnly = false,
  onAddProyectista,
  onRemoveProyectista,
}: ProyectistaSectionProps) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
            Proyectistas
          </h3>
        </div>
        {!readOnly && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onAddProyectista}
            className="gap-2 h-8 rounded-lg text-xs"
          >
            <Plus className="h-3.5 w-3.5" />
            Agregar
          </Button>
        )}
      </div>

      {/* Selected Proyectistas Chips */}
      {selectedProyectistas.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {selectedProyectistas.map((proyectista) => (
            <div
              key={proyectista.id}
              className="inline-flex items-center gap-2.5 px-3 py-2 rounded-lg bg-secondary/50 border border-border hover:bg-secondary/70 hover:border-primary/20 transition-all"
            >
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <HardHat className="h-3.5 w-3.5 text-primary" />
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-semibold text-foreground">
                  {proyectista.nombres} {proyectista.apellidos}
                </span>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                  {proyectista.cip && <span>CIP: {proyectista.cip}</span>}
                  {proyectista.dni && <span>DNI: {proyectista.dni}</span>}
                  {proyectista.cap && <span>CAP: {proyectista.cap}</span>}
                </div>
              </div>
              {!readOnly && (
                <button
                  type="button"
                  onClick={() => onRemoveProyectista(proyectista.id)}
                  className="ml-1 hover:bg-destructive/10 rounded p-0.5 transition-colors"
                  aria-label={`Remover ${proyectista.nombres} ${proyectista.apellidos}`}
                >
                  <X className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                </button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground italic py-2">
          No hay proyectistas seleccionados
        </p>
      )}
    </div>
  );
}
