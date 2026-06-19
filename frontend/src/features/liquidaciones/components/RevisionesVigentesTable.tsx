"use client";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import type { RevisionesVigentesTableProps } from "../types/liquidacion-edificaciones-form.types";

export function RevisionesVigentesTable({
  revisiones,
  selectedIds,
  onToggleRevision,
  isLoading,
}: RevisionesVigentesTableProps) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-2 text-left font-medium">Seleccionar</th>
              <th className="px-4 py-2 text-left font-medium">Especialidad</th>
              <th className="px-4 py-2 text-right font-medium">% Liq.</th>
              <th className="px-4 py-2 text-right font-medium">Derecho Mín.</th>
              <th className="px-4 py-2 text-right font-medium">Derecho Máx.</th>
              <th className="px-4 py-2 text-right font-medium">% Mín. UIT</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {Array.from({ length: 3 }).map((_, i) => (
              <tr key={i} className="hover:bg-muted/30">
                <td className="px-4 py-2">
                  <div className="h-4 w-4 bg-muted animate-pulse rounded" />
                </td>
                <td className="px-4 py-2">
                  <div className="h-4 w-32 bg-muted animate-pulse rounded" />
                </td>
                <td className="px-4 py-2">
                  <div className="h-4 w-16 bg-muted animate-pulse rounded ml-auto" />
                </td>
                <td className="px-4 py-2">
                  <div className="h-4 w-20 bg-muted animate-pulse rounded ml-auto" />
                </td>
                <td className="px-4 py-2">
                  <div className="h-4 w-20 bg-muted animate-pulse rounded ml-auto" />
                </td>
                <td className="px-4 py-2">
                  <div className="h-4 w-16 bg-muted animate-pulse rounded ml-auto" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (revisiones.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-4">
        No hay especialidades/revisiones vigentes disponibles
      </p>
    );
  }

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="px-4 py-2 text-left font-medium">Seleccionar</th>
            <th className="px-4 py-2 text-left font-medium">Especialidad</th>
            <th className="px-4 py-2 text-right font-medium">% Liq.</th>
            <th className="px-4 py-2 text-right font-medium">Derecho Mín.</th>
            <th className="px-4 py-2 text-right font-medium">Derecho Máx.</th>
            <th className="px-4 py-2 text-right font-medium">% Mín. UIT</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {revisiones.map((rev) => (
            <tr key={rev.id} className="hover:bg-muted/30">
              <td className="px-4 py-2">
                <Checkbox
                  checked={selectedIds.includes(rev.id)}
                  onCheckedChange={() => onToggleRevision(rev.id)}
                  disabled={!rev.habilitada}
                />
              </td>
              <td className="px-4 py-2 font-medium">
                {rev.especialidad_nombre}
                {!rev.habilitada && (
                  <Badge variant="secondary" className="ml-2 text-xs">
                    Inhabilitada
                  </Badge>
                )}
              </td>
              <td className="px-4 py-2 text-right">
                {(rev.porcentaje_liquidacion * 100).toFixed(2)}%
              </td>
              <td className="px-4 py-2 text-right">
                S/ {rev.derecho_minimo.toFixed(2)}
              </td>
              <td className="px-4 py-2 text-right">
                {rev.derecho_maximo != null
                  ? `S/ ${rev.derecho_maximo.toFixed(2)}`
                  : "—"}
              </td>
              <td className="px-4 py-2 text-right">
                {(rev.porcentaje_minimo_uit * 100).toFixed(2)}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
