"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { RHCandidatasFiltroValues } from "./RHCandidatasFiltroModal";

interface RHActiveFiltersPanelProps {
  filtros: RHCandidatasFiltroValues;
  onClear: () => void;
}

export function RHActiveFiltersPanel({
  filtros,
  onClear,
}: RHActiveFiltersPanelProps) {
  const activeFilterCount = Object.values(filtros).filter(Boolean).length;
  if (activeFilterCount === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/20 rounded-xl border border-border/60">
      <span className="text-xs font-semibold text-muted-foreground">
        Filtros activos:
      </span>
      {filtros.expediente && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Expediente: {filtros.expediente}
        </span>
      )}
      {filtros.numero && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          N°: {filtros.numero}
        </span>
      )}
      {filtros.propietario && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Propietario: {filtros.propietario}
        </span>
      )}
      {filtros.direccion && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Dirección: {filtros.direccion}
        </span>
      )}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onClear}
        className="h-7 px-2 gap-1 text-xs text-destructive"
      >
        <X className="h-3 w-3" />
        Limpiar
      </Button>
    </div>
  );
}
