/**
 * Vista para lista de Recibos de Honorarios de Inspectores.
 * Ruta: /liquidaciones/recibos-inspectores
 *
 * Usa PageHeader + cards pattern + paginación URL-driven.
 * Filtros: inspector_id (URL-driven)
 *
 * Nota: El endpoint GET /finanzas/recibos-inspectores ahora retorna
 * RecibosHonorariosInspectorMensuales (agrupados por periodo+inspector).
 */
"use client";

import type { LucideIcon } from "lucide-react";
import { Filter, HardHat, Plus, RefreshCw, X } from "lucide-react";
import { useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { ReciboHonorarioInspectorMensualCard } from "@/features/finanzas/components/cards/ReciboHonorarioInspectorMensualCard";
import { RecibosInspectoresFiltroModal } from "@/features/finanzas/components/filtros";
import { RhInspectorMensualModal } from "@/features/finanzas/components/modals/RhInspectorMensualModal";
import { useRecibosInspectores } from "@/features/finanzas/hooks/useRecibosInspectores";
import { useRecibosInspectoresFiltersUrl } from "@/features/finanzas/hooks/useRecibosInspectoresFiltersUrl";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";

const KIND_ICON: LucideIcon = HardHat;

export function RecibosInspectoresView() {
  const [rhModalOpen, setRhModalOpen] = useState(false);
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);
  const { page, pageSize, setPage, setPageSize } = useUrlPagination();
  const { filtros, setFiltros, clearFiltros } =
    useRecibosInspectoresFiltersUrl();

  const { items, total, totalPages, isLoading, isError, refetch } =
    useRecibosInspectores({
      page,
      pageSize,
      inspectorId: filtros.inspector_id,
    });

  const hasActiveFilters = Boolean(filtros.inspector_id);

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Recibos de Honorario - Inspectores"
          description="Listado de recibos de honorarios mensuales de inspectores"
          icon={KIND_ICON}
          actionNodes={
            <>
              <Button
                variant={hasActiveFilters ? "default" : "outline"}
                className="gap-2 h-11 rounded-xl font-bold shrink-0"
                onClick={() => setFiltroModalOpen(true)}
              >
                <Filter className="h-4 w-4" />
                Filtros
                {hasActiveFilters && (
                  <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-primary-foreground/20 text-xs font-bold">
                    1
                  </span>
                )}
              </Button>
              <Button
                className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0"
                onClick={() => setRhModalOpen(true)}
              >
                <Plus className="h-4 w-4" />
                Crear RH
              </Button>
            </>
          }
        />

        {/* Filtros activos */}
        {hasActiveFilters && (
          <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/20 rounded-xl border border-border/60">
            <span className="text-xs font-semibold text-muted-foreground">
              Filtros activos:
            </span>
            {filtros.inspector_id && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Inspector ID: {filtros.inspector_id}
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFiltros}
              className="h-7 px-2 gap-1 text-xs text-destructive"
            >
              <X className="h-3 w-3" />
              Limpiar
            </Button>
          </div>
        )}

        {/* Cards View */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="flex flex-col gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-card rounded-xl border shadow-sm h-48 animate-pulse"
                />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center p-8 text-destructive">
              <p className="font-medium mb-4">Error al cargar los recibos</p>
              <Button variant="outline" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Reintentar
              </Button>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
              <KIND_ICON className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-2">
                No hay recibos de honorario de inspectores registrados
              </p>
              <p className="text-xs text-muted-foreground mb-4">
                Crea un nuevo recibo usando el botón "Crear RH"
              </p>
              <Button
                variant="outline"
                className="gap-2 h-10 rounded-xl font-semibold"
                onClick={() => setRhModalOpen(true)}
              >
                <Plus className="h-4 w-4" />
                Crear RH
              </Button>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {items.map((item) => (
                  <ReciboHonorarioInspectorMensualCard
                    key={item.id}
                    item={item}
                  />
                ))}
              </div>
              {/* Pagination */}
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                totalItems={total}
                pageSize={pageSize}
                onPageChange={setPage}
                onPageSizeChange={setPageSize}
              />
            </>
          )}
        </div>
      </div>

      <RhInspectorMensualModal
        open={rhModalOpen}
        onOpenChange={setRhModalOpen}
        onSuccess={() => {
          setRhModalOpen(false);
          refetch();
        }}
      />

      <RecibosInspectoresFiltroModal
        open={filtroModalOpen}
        onOpenChange={setFiltroModalOpen}
        initialFiltros={filtros}
        onApply={(nuevos) => {
          setFiltros(nuevos);
          setFiltroModalOpen(false);
        }}
      />
    </div>
  );
}
