"use client";

import { FileText } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { LiquidacionGeneralCard } from "../components/LiquidacionGeneralCard";
import { NuevaLiquidacionDropdown } from "../components/NuevaLiquidacionDropdown";
import { useLiquidacionesEdificaciones } from "../hooks/useLiquidacionesEdificaciones";
import type { LiquidacionGeneralListItem } from "../types/liquidacion-general";

/**
 * Vista de Liquidaciones de Edificaciones (list).
 * Muestra tarjetas con información resumida de cada liquidación.
 * Ruta: /liquidaciones/edificaciones
 *
 * @deprecated Use list/detail endpoints — this component uses the list
 *   endpoint (GET /liquidaciones/edificaciones) which returns basic info.
 *   For full detail (proyectistas, especialidades, totales), use the
 *   detail endpoint separately.
 */
export function LiquidacionesEdificacionesView() {
  const {
    items: liquidacionItems,
    total: liquidacionTotal,
    page: liquidacionPage,
    pageSize: liquidacionPageSize,
    isLoading: isLiquidacionLoading,
    isError: isLiquidacionError,
    refetch: refetchLiquidaciones,
    setPage: setLiquidacionPage,
  } = useLiquidacionesEdificaciones({ page: 1, pageSize: 10 });

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
                Liquidaciones de Edificaciones
              </h1>
              <p className="text-sm text-muted-foreground">
                Gestiona las liquidaciones de proyectos de edificación
              </p>
            </div>
          </div>
          <NuevaLiquidacionDropdown onSuccess={refetchLiquidaciones} />
        </div>

        {/* Cards View */}
        <div className="space-y-4">
          {isLiquidacionLoading ? (
            <div className="flex flex-col gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-card rounded-xl border shadow-sm h-48 animate-pulse"
                />
              ))}
            </div>
          ) : isLiquidacionError ? (
            <div className="flex items-center justify-center p-8 text-destructive">
              Error al cargar las liquidaciones
            </div>
          ) : liquidacionItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
              <FileText className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No hay liquidaciones registradas
              </p>
              <div className="mt-4">
                <NuevaLiquidacionDropdown onSuccess={refetchLiquidaciones} />
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {liquidacionItems.map((item) => (
                  <LiquidacionGeneralCard
                    key={item.id}
                    item={item as unknown as LiquidacionGeneralListItem}
                  />
                ))}
              </div>
              {/* Pagination for cards */}
              {liquidacionTotal > liquidacionPageSize && (
                <div className="flex items-center justify-between gap-4 pt-6 border-t border-border/50">
                  <span className="text-xs text-muted-foreground font-medium">
                    Mostrando {liquidacionItems.length} de {liquidacionTotal}{" "}
                    liquidaciones
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setLiquidacionPage(liquidacionPage - 1)}
                      disabled={liquidacionPage <= 1}
                      className="h-9 px-4 text-xs font-semibold"
                    >
                      Anterior
                    </Button>
                    <div className="flex items-center gap-1 px-3 h-9 rounded-md bg-muted border border-border">
                      <span className="text-xs font-bold text-foreground">
                        {liquidacionPage}
                      </span>
                      <span className="text-xs text-muted-foreground">de</span>
                      <span className="text-xs font-bold text-foreground">
                        {Math.ceil(liquidacionTotal / liquidacionPageSize)}
                      </span>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setLiquidacionPage(liquidacionPage + 1)}
                      disabled={
                        liquidacionPage >=
                        Math.ceil(liquidacionTotal / liquidacionPageSize)
                      }
                      className="h-9 px-4 text-xs font-semibold"
                    >
                      Siguiente
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
