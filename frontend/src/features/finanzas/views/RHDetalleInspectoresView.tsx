/**
 * Vista para lista de filas sueltas de DetalleHonorarioInspector (detalle flat).
 * Ruta: /liquidaciones/recibos-inspectores/detalle
 *
 * Tabla CSS-grid con paginación y filtros URL-driven.
 * Filtros opcionales: inspector_cip, periodo, mes, municipalidad_id, numero_liquidacion.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import { Eye, Filter, RefreshCw, Users, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { FilterChip } from "@/components/ui/active-filters";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { RHDetalleVerDetalleModal } from "@/features/finanzas/components/detail/RHDetalleVerDetalleModal";
import { RHDetalleInspectoresFiltroModal } from "@/features/finanzas/components/filtros";
import { RHDetalleInspectoresTable } from "@/features/finanzas/components/tables/RHDetalleInspectoresTable";
import type {
  DetalleInspectorRow,
  RHDetalleRowAction,
} from "@/features/finanzas/components/tables/RHDetalleTable.types";
import { useRHDetalleInspectores } from "@/features/finanzas/hooks/useRHDetalleInspectores";
import { useRHDetalleInspectoresFiltersUrl } from "@/features/finanzas/hooks/useRHDetalleInspectoresFiltersUrl";
import { useMunicipalidades } from "@/features/liquidaciones/hooks/useMunicipalidades";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";

const KIND_ICON: LucideIcon = Users;

export function RHDetalleInspectoresView() {
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);
  const [verDetalleId, setVerDetalleId] = useState<string | null>(null);

  const { page, pageSize, setPage } = useUrlPagination();
  const { filtros, setFiltros, clearFiltros } =
    useRHDetalleInspectoresFiltersUrl();

  const { items, total, totalPages, isLoading, isError, refetch } =
    useRHDetalleInspectores({
      page,
      pageSize,
      inspectorCip: filtros.inspector_cip,
      periodo: filtros.periodo,
      mes: filtros.mes,
      municipalidadId: filtros.municipalidad_id,
      numeroLiquidacion: filtros.numero_liquidacion,
    });

  const { data: municipalidades = [] } = useMunicipalidades();
  const municipalidadNombreById = useMemo(() => {
    const map = new Map<string, string>();
    for (const m of municipalidades) {
      const codigoPrefix = m.codigo ? `${m.codigo} - ` : "";
      map.set(m.id, `${codigoPrefix}${m.nombre}`);
    }
    return map;
  }, [municipalidades]);

  /**
   * Quita un único filtro del estado URL-driven. Mantiene el resto.
   */
  const removeFilter = (key: keyof typeof filtros) => {
    const next = { ...filtros };
    delete next[key];
    setFiltros(next);
  };

  const hasActiveFilters = Boolean(
    filtros.inspector_cip ||
      filtros.periodo ||
      filtros.mes ||
      filtros.municipalidad_id ||
      filtros.numero_liquidacion,
  );

  const activeFilterCount = [
    filtros.inspector_cip,
    filtros.periodo,
    filtros.mes,
    filtros.municipalidad_id,
    filtros.numero_liquidacion,
  ].filter(Boolean).length;

  const renderActions = (item: DetalleInspectorRow): RHDetalleRowAction[] => {
    const liquidacionId = item.inspector_liquidacion?.liquidacion?.id ?? null;
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

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Detalle de Honorarios - Inspectores"
          description="Listado de filas detalle de recibos de honorarios de inspectores"
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
                  {activeFilterCount}
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
            {filtros.inspector_cip && (
              <FilterChip
                label="CIP"
                value={filtros.inspector_cip}
                onRemove={() => removeFilter("inspector_cip")}
              />
            )}
            {filtros.periodo && (
              <FilterChip
                label="Año"
                value={String(filtros.periodo)}
                onRemove={() => removeFilter("periodo")}
              />
            )}
            {filtros.mes && (
              <FilterChip
                label="Mes"
                value={String(filtros.mes)}
                onRemove={() => removeFilter("mes")}
              />
            )}
            {filtros.municipalidad_id && (
              <FilterChip
                label="Municipalidad"
                value={
                  municipalidadNombreById.get(filtros.municipalidad_id) ??
                  filtros.municipalidad_id
                }
                onRemove={() => removeFilter("municipalidad_id")}
              />
            )}
            {filtros.numero_liquidacion && (
              <FilterChip
                label="N° Liquidación"
                value={String(filtros.numero_liquidacion)}
                onRemove={() => removeFilter("numero_liquidacion")}
              />
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
            <RHDetalleInspectoresTable
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

      <RHDetalleInspectoresFiltroModal
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
