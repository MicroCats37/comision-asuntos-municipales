"use client";

import { FileText } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { kindLabel } from "../components/LiquidacionGeneralCard";
import { NuevaLiquidacionDropdown } from "../components/NuevaLiquidacionDropdown";
import { useLiquidacionesGenerales } from "../hooks/useLiquidacionesGenerales";
import type { LiquidacionGeneralListItem } from "../types/liquidacion-general";

/**
 * Vista de Liquidaciones Generales.
 * Muestra lista simple de liquidaciones con información de proyecto.
 * Ruta: /liquidaciones
 */
export function LiquidacionesGeneralesView() {
  const {
    items: liquidaciones,
    total,
    page,
    pageSize,
    isLoading,
    isError,
    refetch,
    setPage,
  } = useLiquidacionesGenerales({ page: 1, pageSize: 10 });

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="page-section">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-black tracking-tight">
                Liquidaciones
              </h1>
              <p className="text-sm text-muted-foreground">
                Lista general de liquidaciones de edificación
              </p>
            </div>
          </div>
          <NuevaLiquidacionDropdown onSuccess={refetch} />
        </div>

        {/* Table View */}
        <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-3 text-left text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    Código
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    Proyecto
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    Municipalidad
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    Rev
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    Estado
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    Total
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-bold text-muted-foreground uppercase tracking-wider">
                    Fecha
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {isLoading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i} className="animate-pulse">
                      {[...Array(7)].map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-muted rounded w-20" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : isError ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-4 py-8 text-center text-destructive"
                    >
                      Error al cargar las liquidaciones
                    </td>
                  </tr>
                ) : liquidaciones.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center">
                      <FileText className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                      <p className="text-muted-foreground text-sm">
                        No hay liquidaciones registradas
                      </p>
                      <div className="mt-4">
                        <NuevaLiquidacionDropdown onSuccess={refetch} />
                      </div>
                    </td>
                  </tr>
                ) : (
                  liquidaciones.map((item: LiquidacionGeneralListItem) => (
                    <tr
                      key={item.id}
                      className="hover:bg-muted/30 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <span className="text-sm font-mono font-semibold text-primary">
                          {item.public_id}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium text-sm text-foreground">
                            {item.proyecto?.nombre || "—"}
                          </p>
                          <p className="text-xs text-muted-foreground font-mono">
                            {item.proyecto?.public_id}
                          </p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-xs font-semibold">
                          {kindLabel(item.tipo_liquidacion)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-muted-foreground">
                          {item.municipalidad?.nombre || "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-sm font-medium">
                          N° {item.numero_revision}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${item.estado === "PAGADO" ? "bg-emerald-500/10 text-secondary-foreground border border-emerald-500/20" : item.estado === "PENDIENTE" ? "bg-amber-500/10 text-amber-600 border border-amber-500/20" : item.estado === "ANULADO" ? "bg-destructive/10 text-destructive border border-destructive/20" : "bg-muted text-muted-foreground border border-border"}`}
                        >
                          {item.estado}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-sm font-bold text-primary">
                          S/{" "}
                          {item.total.toLocaleString("es-PE", {
                            minimumFractionDigits: 2,
                          })}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-muted-foreground">
                          {item.fecha_registro
                            ? new Date(item.fecha_registro).toLocaleDateString(
                                "es-PE",
                                {
                                  day: "2-digit",
                                  month: "short",
                                  year: "numeric",
                                },
                              )
                            : "—"}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > pageSize && (
            <div className="flex items-center justify-between gap-4 px-4 py-3 border-t border-border/60 bg-muted/30">
              <span className="text-xs text-muted-foreground font-medium">
                Mostrando {liquidaciones.length} de {total} liquidaciones
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page - 1)}
                  disabled={page <= 1}
                  className="h-9 px-4 text-xs font-semibold"
                >
                  Anterior
                </Button>
                <div className="flex items-center gap-1 px-3 h-9 rounded-md bg-muted border border-border">
                  <span className="text-xs font-bold text-foreground">
                    {page}
                  </span>
                  <span className="text-xs text-muted-foreground">de</span>
                  <span className="text-xs font-bold text-foreground">
                    {totalPages}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(page + 1)}
                  disabled={page >= totalPages}
                  className="h-9 px-4 text-xs font-semibold"
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
