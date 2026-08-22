/**
 * Vista para lista de Recibos de Honorarios de Inspectores.
 * Ruta: /liquidaciones/recibos-inspectores
 *
 * Usa PageHeader + cards pattern + paginación.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import { FileSpreadsheet, HardHat, Plus, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { ReciboInspectorCard } from "@/features/finanzas/components/cards/ReciboInspectorCard";
import { CrearReciboInspectorModal } from "@/features/finanzas/components/modals/CrearReciboInspectorModal";
import { RhInspectorMensualModal } from "@/features/finanzas/components/modals/RhInspectorMensualModal";
import { useRecibosInspectores } from "@/features/finanzas/hooks/useRecibosInspectores";

const KIND_ICON: LucideIcon = HardHat;

export function RecibosInspectoresView() {
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [rhModalOpen, setRhModalOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const { items, total, totalPages, isLoading, isError, refetch } =
    useRecibosInspectores({
      page,
      pageSize,
    });

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Recibos de Honorario - Inspectores"
          description="Listado de recibos de honorarios de inspectores"
          icon={KIND_ICON}
          actionNodes={
            <>
              <Button
                variant="outline"
                className="gap-2 h-11 rounded-xl font-bold shrink-0"
                onClick={() => setRhModalOpen(true)}
              >
                <FileSpreadsheet className="h-4 w-4" />
                Importar RH Mensual
              </Button>
              <Button
                className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0"
                onClick={() => setFormModalOpen(true)}
              >
                <Plus className="h-4 w-4" />
                Nuevo Recibo
              </Button>
            </>
          }
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
                Crea un nuevo recibo usando el botón "Nuevo Recibo"
              </p>
              <Button
                variant="outline"
                className="gap-2 h-10 rounded-xl font-semibold"
                onClick={() => setFormModalOpen(true)}
              >
                <Plus className="h-4 w-4" />
                Nuevo Recibo
              </Button>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {items.map((item) => (
                  <ReciboInspectorCard key={item.id} item={item} />
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

      <CrearReciboInspectorModal
        open={formModalOpen}
        onOpenChange={setFormModalOpen}
        onSuccess={() => {
          setFormModalOpen(false);
          refetch();
        }}
      />

      <RhInspectorMensualModal
        open={rhModalOpen}
        onOpenChange={setRhModalOpen}
        onSuccess={() => {
          setRhModalOpen(false);
          refetch();
        }}
      />
    </div>
  );
}
