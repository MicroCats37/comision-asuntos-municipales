/**
 * Vista para lista de Recibos de Honorarios de Delegados.
 * Ruta: /liquidaciones/recibos-delegados
 *
 * Usa PageHeader + cards pattern + paginación.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import { Plus, RefreshCw, User } from "lucide-react";
import { useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { ReciboHonorarioCard } from "@/features/finanzas/components/cards/ReciboHonorarioCard";
import { ReciboHonorarioFormModal } from "@/features/finanzas/components/modals/ReciboHonorarioFormModal";
import { useRecibosDelegados } from "@/features/finanzas/hooks/useRecibosDelegados";

const KIND_ICON: LucideIcon = User;

export function RecibosDelegadosView() {
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const { items, total, totalPages, isLoading, isError, refetch } =
    useRecibosDelegados({
      page,
      pageSize,
    });

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Recibos de Honorario - Delegados"
          description="Listado de recibos de honorarios de delegados"
          icon={KIND_ICON}
          actionNodes={
            <Button
              className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0"
              onClick={() => setFormModalOpen(true)}
            >
              <Plus className="h-4 w-4" />
              Nuevo Recibo
            </Button>
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
                No hay recibos de honorario registrados
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
                  <ReciboHonorarioCard key={item.id} item={item} />
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

      <ReciboHonorarioFormModal
        open={formModalOpen}
        onOpenChange={setFormModalOpen}
        onSuccess={() => {
          setFormModalOpen(false);
          refetch();
        }}
      />
    </div>
  );
}
