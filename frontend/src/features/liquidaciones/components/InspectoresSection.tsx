"use client";

import { Loader2, UserCheck } from "lucide-react";
import type { InspectorVigente } from "@/features/inspectores/types/inspectores.types";

interface InspectoresSectionProps {
  inspectores: InspectorVigente[];
  selectedIds: string[];
  isLoading?: boolean;
  onToggleInspector: (id: string) => void;
}

export function InspectoresSection({
  inspectores,
  selectedIds,
  isLoading = false,
  onToggleInspector,
}: InspectoresSectionProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
          <UserCheck className="h-4 w-4" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            Inspectores
          </h3>
        </div>
        <div className="flex items-center gap-2 py-2">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          <span className="text-sm text-muted-foreground">
            Cargando inspectores...
          </span>
        </div>
      </div>
    );
  }

  if (inspectores.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
          <UserCheck className="h-4 w-4" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            Inspectores
          </h3>
        </div>
        <p className="text-sm text-muted-foreground italic py-2">
          No hay inspectores elegibles para esta inspección de obra
        </p>
      </div>
    );
  }

  const groupedByEspecialidad = inspectores.reduce<
    Record<string, InspectorVigente[]>
  >((acc, inspector) => {
    const specialtyName = inspector.especialidad?.nombre ?? "Sin especialidad";
    if (!acc[specialtyName]) acc[specialtyName] = [];
    acc[specialtyName].push(inspector);
    return acc;
  }, {});

  const sortedSpecialties = Object.keys(groupedByEspecialidad).sort((a, b) =>
    a.localeCompare(b, undefined, { sensitivity: "base" }),
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 bg-primary text-primary-foreground rounded-t-xl">
        <UserCheck className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide">
          Inspectores
        </h3>
        <span className="ml-auto text-[10px] font-medium opacity-75">
          ({selectedIds.length} seleccionado
          {selectedIds.length !== 1 ? "s" : ""})
        </span>
      </div>

      <div className="space-y-6">
        {sortedSpecialties.map((specialtyName) => (
          <div key={specialtyName} className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="h-px flex-1 bg-border/60" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground shrink-0">
                {specialtyName}
              </span>
              <div className="h-px flex-1 bg-border/60" />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 w-full">
              {groupedByEspecialidad[specialtyName].map((inspector) => {
                const isSelected = selectedIds.includes(inspector.id);
                return (
                  <button
                    key={inspector.id}
                    type="button"
                    onClick={() => onToggleInspector(inspector.id)}
                    className={`w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl border transition-all text-left ${
                      isSelected
                        ? "bg-primary/10 border-primary/60 ring-2 ring-primary/30 hover:bg-primary/15 hover:border-primary/80"
                        : "bg-secondary/30 border-border/70 hover:bg-secondary/60 hover:border-primary/40"
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${isSelected ? "bg-primary text-primary-foreground" : "bg-muted/80 text-muted-foreground"}`}
                      >
                        <UserCheck className="h-4 w-4" />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className="text-sm font-bold text-foreground truncate">
                          {inspector.nombre_completo}
                        </span>
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground mt-1">
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-muted/70 text-foreground/80 font-medium whitespace-nowrap">
                            CIP {inspector.cip}
                          </span>
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-secondary/70 text-muted-foreground/80 whitespace-nowrap">
                            Reg. {inspector.numero_registro}
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
