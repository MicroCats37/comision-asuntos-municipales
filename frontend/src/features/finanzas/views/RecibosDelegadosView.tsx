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
import { FileSpreadsheet, Filter, Plus, RefreshCw, User } from "lucide-react";
import { useMemo, useState } from "react";
import { useConfirmationDialog } from "@/components/confirmationDialog/useConfirmationDialog";
import { Pagination } from "@/components/genericPagination/Pagination";
import { ActiveFiltersPanel } from "@/components/ui/active-filters";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { ReciboHonorarioDelegadoMensualCard } from "@/features/finanzas/components/cards/ReciboHonorarioDelegadoMensualCard";
import { RecibosDelegadosFiltroModal } from "@/features/finanzas/components/filtros";
import { RHMensualExcelModal } from "@/features/finanzas/components/modals/RHMensualExcelModal";
import { RhDelegadoMensualModal } from "@/features/finanzas/components/modals/RhDelegadoMensualModal";
import { useEliminarReciboDelegado } from "@/features/finanzas/hooks/useEliminarReciboDelegado";
import { useRecibosDelegados } from "@/features/finanzas/hooks/useRecibosDelegados";
import { useRecibosDelegadosFiltersUrl } from "@/features/finanzas/hooks/useRecibosDelegadosFiltersUrl";
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import { useMunicipalidades } from "@/features/liquidaciones/hooks/useMunicipalidades";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";

const KIND_ICON: LucideIcon = User;

export function RecibosDelegadosView() {
  const [rhModalOpen, setRhModalOpen] = useState(false);
  const [rhEnEdicion, setRhEnEdicion] =
    useState<ReciboHonorarioDelegadoMensual | null>(null);
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);
  const [excelModalOpen, setExcelModalOpen] = useState(false);
  const { page, pageSize, setPage, setPageSize } = useUrlPagination();
  const { filtros, setFiltros, clearFiltros } = useRecibosDelegadosFiltersUrl();
  const { confirm, Dialog } = useConfirmationDialog();
  const eliminarMutation = useEliminarReciboDelegado();

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

  const handleDelete = (id: string) => {
    confirm({
      title: "Eliminar recibo de delegado",
      description:
        "¿Estás seguro de que deseas eliminar este recibo de honorario mensual? Esta acción no se puede deshacer.",
      confirmLabel: "Eliminar",
      variant: "danger",
    }).then((confirmed) => {
      if (confirmed) {
        eliminarMutation.eliminar(id);
      }
    });
  };

  const activeFilterCount = [
    filtros.delegado_cip,
    filtros.municipalidad_id,
    filtros.periodo,
    filtros.mes,
  ].filter(Boolean).length;

  /** Abre el wizard de RH mensual en modo edición sobre el recibo elegido. */
  const handleEdit = (item: ReciboHonorarioDelegadoMensual) => {
    setRhEnEdicion(item);
    setRhModalOpen(true);
  };

  /** Abre el wizard de RH mensual en modo creación. */
  const handleCreate = () => {
    setRhEnEdicion(null);
    setRhModalOpen(true);
  };

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
                variant="outline"
                className="gap-2 h-11 rounded-xl font-bold shrink-0"
                onClick={() => setExcelModalOpen(true)}
              >
                <FileSpreadsheet className="h-4 w-4" />
                Exportar Excel
              </Button>
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
                onClick={handleCreate}
              >
                <Plus className="h-4 w-4" />
                Crear RH
              </Button>
            </>
          }
        />

        {/* Filtros activos — cada chip removible individualmente */}
        <ActiveFiltersPanel
          entries={[
            ...(filtros.delegado_cip
              ? [
                  {
                    key: "delegado_cip" as const,
                    label: "CIP",
                    value: filtros.delegado_cip,
                  },
                ]
              : []),
            ...(filtros.periodo
              ? [
                  {
                    key: "periodo" as const,
                    label: "Año",
                    value: String(filtros.periodo),
                  },
                ]
              : []),
            ...(filtros.mes
              ? [
                  {
                    key: "mes" as const,
                    label: "Mes",
                    value: String(filtros.mes),
                  },
                ]
              : []),
            ...(filtros.municipalidad_id
              ? [
                  {
                    key: "municipalidad_id" as const,
                    label: "Municipalidad",
                    value:
                      municipalidadNombreById.get(filtros.municipalidad_id) ??
                      filtros.municipalidad_id,
                  },
                ]
              : []),
          ]}
          onRemove={removeFilter}
          onClearAll={clearFiltros}
        />

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
                onClick={handleCreate}
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
                    onDelete={handleDelete}
                    onEdit={handleEdit}
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

      <RHMensualExcelModal
        open={excelModalOpen}
        onOpenChange={setExcelModalOpen}
        variante="delegados"
      />

      <RhDelegadoMensualModal
        open={rhModalOpen}
        onOpenChange={(open) => {
          setRhModalOpen(open);
          if (!open) setRhEnEdicion(null);
        }}
        editContext={rhEnEdicion ? { rh: rhEnEdicion } : null}
        onSuccess={() => {
          setRhModalOpen(false);
          setRhEnEdicion(null);
          refetch();
        }}
      />

      {Dialog}

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
