/**
 * Vista para lista de Recibos de Honorarios de Inspectores.
 * Ruta: /liquidaciones/recibos-inspectores
 *
 * Usa PageHeader + cards pattern + paginación URL-driven.
 * Filtros: inspector_cip, periodo, mes (URL-driven)
 *
 * Nota: El endpoint GET /finanzas/recibos-inspectores ahora retorna
 * RecibosHonorariosInspectorMensuales (agrupados por periodo+inspector).
 */
"use client";

import type { LucideIcon } from "lucide-react";
import {
  FileSpreadsheet,
  Filter,
  HardHat,
  Plus,
  RefreshCw,
} from "lucide-react";
import { useState } from "react";
import { useConfirmationDialog } from "@/components/confirmationDialog/useConfirmationDialog";
import { Pagination } from "@/components/genericPagination/Pagination";
import { ActiveFiltersPanel } from "@/components/ui/active-filters";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { ReciboHonorarioInspectorMensualCard } from "@/features/finanzas/components/cards/ReciboHonorarioInspectorMensualCard";
import { RecibosInspectoresFiltroModal } from "@/features/finanzas/components/filtros";
import { RHMensualExcelModal } from "@/features/finanzas/components/modals/RHMensualExcelModal";
import { RhInspectorMensualModal } from "@/features/finanzas/components/modals/RhInspectorMensualModal";
import { useEliminarReciboInspector } from "@/features/finanzas/hooks/useEliminarReciboInspector";
import { useRecibosInspectores } from "@/features/finanzas/hooks/useRecibosInspectores";
import { useRecibosInspectoresFiltersUrl } from "@/features/finanzas/hooks/useRecibosInspectoresFiltersUrl";
import type { ReciboHonorarioInspectorMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";

const KIND_ICON: LucideIcon = HardHat;

export function RecibosInspectoresView() {
  const [rhModalOpen, setRhModalOpen] = useState(false);
  const [rhEnEdicion, setRhEnEdicion] =
    useState<ReciboHonorarioInspectorMensual | null>(null);
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);
  const [excelModalOpen, setExcelModalOpen] = useState(false);
  const { page, pageSize, setPage, setPageSize } = useUrlPagination();
  const { filtros, setFiltros, clearFiltros } =
    useRecibosInspectoresFiltersUrl();
  const { confirm, Dialog } = useConfirmationDialog();
  const eliminarMutation = useEliminarReciboInspector();

  const { items, total, totalPages, isLoading, isError, refetch } =
    useRecibosInspectores({
      page,
      pageSize,
      inspectorCip: filtros.inspector_cip,
      periodo: filtros.periodo,
      mes: filtros.mes,
    });

  const activeFilterCount = [
    filtros.inspector_cip,
    filtros.periodo,
    filtros.mes,
  ].filter(Boolean).length;
  const hasActiveFilters = activeFilterCount > 0;

  const removeFilter = (key: keyof typeof filtros) => {
    const next = { ...filtros };
    delete next[key];
    setFiltros(next);
  };

  /** Abre el wizard de RH mensual en modo edición sobre el recibo elegido. */
  const handleEdit = (item: ReciboHonorarioInspectorMensual) => {
    setRhEnEdicion(item);
    setRhModalOpen(true);
  };

  /** Abre el wizard de RH mensual en modo creación. */
  const handleCreate = () => {
    setRhEnEdicion(null);
    setRhModalOpen(true);
  };

  const handleDelete = (id: string) => {
    confirm({
      title: "Eliminar recibo de inspector",
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
            ...(filtros.inspector_cip
              ? [
                  {
                    key: "inspector_cip" as const,
                    label: "CIP",
                    value: filtros.inspector_cip,
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
                No hay recibos de honorario de inspectores registrados
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
                  <ReciboHonorarioInspectorMensualCard
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
        variante="inspectores"
      />

      <RhInspectorMensualModal
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
