/**
 * Vista para lista de filas sueltas de DetalleHonorarioDelegado (detalle flat).
 * Ruta: /liquidaciones/recibos-delegados/detalle
 *
 * Tabla CSS-grid con paginación y filtros URL-driven.
 * Filtros backend: delegado_id, periodo, mes, municipalidad_id, tipo_liquidacion_id, numero_liquidacion
 *
 * Nota: periodo y tipo_liquidacion_id son obligatorios. Sin ellos se muestra estado vacío guiado.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import { Eye, Filter, RefreshCw, User, X } from "lucide-react";
import { useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { RHDetalleVerDetalleModal } from "@/features/finanzas/components/detail/RHDetalleVerDetalleModal";
import { RHDetalleDelegadosFiltroModal } from "@/features/finanzas/components/filtros";
import { RHDetalleDelegadosTable } from "@/features/finanzas/components/tables/RHDetalleDelegadosTable";
import type {
  DetalleDelegadoRow,
  RHDetalleRowAction,
} from "@/features/finanzas/components/tables/RHDetalleTable.types";
import { useRHDetalleDelegados } from "@/features/finanzas/hooks/useRHDetalleDelegados";
import { useRHDetalleDelegadosFiltersUrl } from "@/features/finanzas/hooks/useRHDetalleDelegadosFiltersUrl";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";

const KIND_ICON: LucideIcon = User;

export function RHDetalleDelegadosView() {
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);
  const [verDetalleId, setVerDetalleId] = useState<string | null>(null);

  const { page, pageSize, setPage } = useUrlPagination();
  const { filtros, setFiltros, clearFiltros } =
    useRHDetalleDelegadosFiltersUrl();

  // Required filters must be present to enable the query
  const hasRequiredFilters = Boolean(
    filtros.periodo && filtros.tipo_liquidacion_id,
  );

  const { items, total, totalPages, isLoading, isError, refetch } =
    useRHDetalleDelegados({
      page,
      pageSize,
      delegadoCip: filtros.delegado_cip,
      periodo: filtros.periodo,
      mes: filtros.mes,
      municipalidadId: filtros.municipalidad_id,
      tipoLiquidacionId: filtros.tipo_liquidacion_id,
      numeroLiquidacion: filtros.numero_liquidacion,
      enabled: hasRequiredFilters,
    });

  const hasActiveFilters = Boolean(
    filtros.delegado_cip ||
      filtros.periodo ||
      filtros.mes ||
      filtros.municipalidad_id ||
      filtros.tipo_liquidacion_id ||
      filtros.numero_liquidacion,
  );

  const renderActions = (item: DetalleDelegadoRow): RHDetalleRowAction[] => {
    const liquidacionId = item.delegado_liquidacion?.liquidacion?.id ?? null;
    return [
      {
        icon: Eye,
        label: "Ver detalle",
        variant: "primary",
        hidden: !liquidacionId,
        onAction: () => setVerDetalleId(liquidacionId),
      },
    ];
  };

  // Guided empty state when required filters are missing
  const showGuidedEmpty = !hasRequiredFilters && !isLoading;

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Detalle de Honorarios - Delegados"
          description="Listado de filas detalle de recibos de honorarios de delegados"
          icon={KIND_ICON}
          actionNodes={
            <Button
              variant={hasActiveFilters ? "default" : "outline"}
              className="gap-2 h-11 rounded-xl font-bold shrink-0"
              onClick={() => setFiltroModalOpen(true)}
            >
              <Filter className="h-4 w-4" />
              Filtros
              {hasActiveFilters && (
                <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-primary-foreground/20 text-xs font-bold">
                  {
                    [
                      filtros.delegado_cip,
                      filtros.periodo,
                      filtros.mes,
                      filtros.municipalidad_id,
                      filtros.tipo_liquidacion_id,
                      filtros.numero_liquidacion,
                    ].filter(Boolean).length
                  }
                </span>
              )}
            </Button>
          }
        />

        {/* Filtros activos */}
        {hasActiveFilters && (
          <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/20 rounded-xl border border-border/60">
            <span className="text-xs font-semibold text-muted-foreground">
              Filtros activos:
            </span>
            {filtros.delegado_cip && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                CIP: {filtros.delegado_cip}
              </span>
            )}
            {filtros.periodo && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Año: {filtros.periodo}
              </span>
            )}
            {filtros.mes && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Mes: {filtros.mes}
              </span>
            )}
            {filtros.municipalidad_id && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Municipalidad ID: {filtros.municipalidad_id}
              </span>
            )}
            {filtros.tipo_liquidacion_id && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Tipo Liquidación ID: {filtros.tipo_liquidacion_id}
              </span>
            )}
            {filtros.numero_liquidacion && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                N° Liquidación: {filtros.numero_liquidacion}
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

        {/* Table */}
        {showGuidedEmpty && (
          <div className="border rounded-lg px-3 py-12 text-center">
            <p className="text-muted-foreground font-medium mb-1">
              Selecciona año y tipo de liquidación para consultar
            </p>
            <p className="text-muted-foreground text-sm">
              Los filtros obligatorios no están completos. Aplica los filtros
              para ver resultados.
            </p>
          </div>
        )}
        {isLoading && (
          <div className="flex flex-col gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-card rounded-xl border shadow-sm h-16 animate-pulse"
              />
            ))}
          </div>
        )}
        {isError && (
          <div className="flex flex-col items-center justify-center p-8 text-destructive">
            <p className="font-medium mb-4">Error al cargar los datos</p>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Reintentar
            </Button>
          </div>
        )}

        {!isLoading && !isError && (
          <>
            <RHDetalleDelegadosTable
              items={items}
              renderActions={renderActions}
            />

            {/* Empty state */}
            {items.length === 0 && (
              <div className="border rounded-lg px-3 py-8 text-center text-muted-foreground">
                No se encontraron filas detalle
              </div>
            )}

            {/* Pagination */}
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Total: {total} filas
              </p>
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                onPageChange={(p) => setPage(p)}
              />
            </div>
          </>
        )}
      </div>

      {/* Ver detalle modal */}
      <RHDetalleVerDetalleModal
        liquidacionId={verDetalleId}
        open={verDetalleId !== null}
        onOpenChange={(open) => {
          if (!open) setVerDetalleId(null);
        }}
      />

      <RHDetalleDelegadosFiltroModal
        open={filtroModalOpen}
        onOpenChange={setFiltroModalOpen}
        initialFiltros={{
          ...filtros,
          periodo: filtros.periodo ?? new Date().getFullYear(),
          mes: filtros.mes ?? new Date().getMonth() + 1,
        }}
        onApply={(nuevos) => {
          setFiltros(nuevos);
          setFiltroModalOpen(false);
        }}
      />
    </div>
  );
}
