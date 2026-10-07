/**
 * Vista para lista de Recibos de Honorarios de Delegados.
 * Ruta: /liquidaciones/recibos-delegados
 *
 * Usa PageHeader + cards pattern + paginación URL-driven.
 * Filtros URL-driven: delegado_cip, municipalidad_id, periodo, mes.
 * Arquitectura alineada con RHDetalleDelegadosView: chips removibles con FilterChip.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import { Filter, Plus, RefreshCw, User, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { ReciboHonorarioDelegadoMensualCard } from "@/features/finanzas/components/cards/ReciboHonorarioDelegadoMensualCard";
import { RecibosDelegadosFiltroModal } from "@/features/finanzas/components/filtros";
import { RhDelegadoMensualModal } from "@/features/finanzas/components/modals/RhDelegadoMensualModal";
import { useRecibosDelegados } from "@/features/finanzas/hooks/useRecibosDelegados";
import { useRecibosDelegadosFiltersUrl } from "@/features/finanzas/hooks/useRecibosDelegadosFiltersUrl";
import { useMunicipalidades } from "@/features/liquidaciones/hooks/useMunicipalidades";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";

const KIND_ICON: LucideIcon = User;

/**
 * Chip removible para un filtro activo individual. Click en la X quita SOLO ese filtro.
 */
function FilterChip({
  label,
  value,
  onRemove,
}: {
  label: string;
  value: string;
  onRemove: () => void;
}) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 pl-2.5 pr-1 py-1 text-xs font-medium">
      <span className="text-foreground/70 font-semibold">{label}:</span>
      <span className="font-bold">{value}</span>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Quitar filtro ${label}: ${value}`}
        className="inline-flex items-center justify-center h-5 w-5 rounded-full hover:bg-primary/20 text-primary transition-colors"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

export function RecibosDelegadosView() {
  const [rhModalOpen, setRhModalOpen] = useState(false);
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);
  const { page, pageSize, setPage, setPageSize } = useUrlPagination();
  const { filtros, setFiltros, clearFiltros } = useRecibosDelegadosFiltersUrl();

  const { data: municipalidades = [] } = useMunicipalidades();
  const municipalidadNombreById = useMemo(() => {
    const map = new Map<string, string>();
    for (const m of municipalidades) {
      const codigoPrefix = m.codigo ? `${m.codigo} - ` : "";
      map.set(m.id, `${codigoPrefix}${m.nombre}`);
    }
    return map;
  }, [municipalidades]);

  const { items, total, totalPages, isLoading, isError, refetch } =
    useRecibosDelegados({
      page,
      pageSize,
      delegadoCip: filtros.delegado_cip,
      municipalidadId: filtros.municipalidad_id,
      periodo: filtros.periodo,
      mes: filtros.mes,
    });

  const hasActiveFilters = Boolean(
    filtros.delegado_cip ||
      filtros.municipalidad_id ||
      filtros.periodo ||
      filtros.mes,
  );

  const activeFilterCount = [
    filtros.delegado_cip,
    filtros.municipalidad_id,
    filtros.periodo,
    filtros.mes,
  ].filter(Boolean).length;

  const removeFilter = (key: keyof typeof filtros) => {
    const next = { ...filtros };
    delete next[key];
    setFiltros(next);
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Recibos de Honorario - Delegados"
          description="Listado de recibos de honorarios de delegados"
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
                    {activeFilterCount}
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

        {/* Filtros activos — cada chip removible individualmente */}
        {hasActiveFilters && (
          <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/20 rounded-xl border border-border/60">
            <span className="text-xs font-semibold text-muted-foreground">
              Filtros activos:
            </span>

            {filtros.delegado_cip && (
              <FilterChip
                label="CIP"
                value={filtros.delegado_cip}
                onRemove={() => removeFilter("delegado_cip")}
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

            <Button
              variant="ghost"
              size="sm"
              onClick={clearFiltros}
              className="h-7 px-2 gap-1 text-xs text-destructive"
            >
              <X className="h-3 w-3" />
              Limpiar todo
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
                No hay recibos de honorario registrados
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
                  <ReciboHonorarioDelegadoMensualCard
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

      <RhDelegadoMensualModal
        open={rhModalOpen}
        onOpenChange={setRhModalOpen}
        onSuccess={() => {
          setRhModalOpen(false);
          refetch();
        }}
      />

      <RecibosDelegadosFiltroModal
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
