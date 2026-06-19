"use client";

import { FileText, Plus } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { LiquidacionEdificacionFormModal } from "../components/LiquidacionEdificacionFormModal";
import { LiquidacionSnapshotCard } from "../components/LiquidacionSnapshotCard";
import { NuevaRevisionFormModal } from "../components/NuevaRevisionFormModal";
import { useLiquidacionesSnapshots } from "../hooks/useLiquidaciones";
import type { LiquidacionSnapshotListItem } from "../types/liquidacion-edificaciones";

export function LiquidacionesView() {
  const [formOpen, setFormOpen] = useState(false);
  const [nuevaRevisionBase, setNuevaRevisionBase] = useState<LiquidacionSnapshotListItem | null>(null);

  const {
    items: snapshotItems,
    total: snapshotTotal,
    page: snapshotPage,
    pageSize: snapshotPageSize,
    isLoading: isSnapshotLoading,
    isError: isSnapshotError,
    refetch: refetchSnapshots,
    setPage: setSnapshotPage,
  } = useLiquidacionesSnapshots({ page: 1, pageSize: 10 });

  const handleOpenCreate = () => {
    setFormOpen(true);
  };

  const handleFormSuccess = () => {
    refetchSnapshots();
  };

  const handleNuevaRevision = (item: LiquidacionSnapshotListItem) => {
    setNuevaRevisionBase(item);
  };

  const handleNuevaRevisionSuccess = () => {
    setNuevaRevisionBase(null);
    refetchSnapshots();
  };

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
          <Button
            onClick={handleOpenCreate}
            className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20"
          >
            <Plus className="h-4 w-4" />
            Nueva Liquidación
          </Button>
        </div>

        {/* Cards View */}
        <div className="space-y-4">
          {isSnapshotLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-card rounded-xl border shadow-sm h-64 animate-pulse"
                />
              ))}
            </div>
          ) : isSnapshotError ? (
            <div className="flex items-center justify-center p-8 text-destructive">
              Error al cargar las liquidaciones
            </div>
          ) : snapshotItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
              <FileText className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No hay liquidaciones registradas</p>
              <Button
                onClick={handleOpenCreate}
                className="mt-4 gap-2"
                variant="outline"
              >
                <Plus className="h-4 w-4" />
                Nueva Liquidación
              </Button>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {snapshotItems.map((item) => (
                  <LiquidacionSnapshotCard
                    key={item.liquidacion_id}
                    item={item}
                    onNuevaRevision={handleNuevaRevision}
                  />
                ))}
              </div>
              {/* Pagination for cards */}
              {snapshotTotal > snapshotPageSize && (
                <div className="flex items-center justify-between gap-4 pt-6 border-t border-border/50">
                  <span className="text-xs text-muted-foreground font-medium">
                    Mostrando {snapshotItems.length} de {snapshotTotal} liquidaciones
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSnapshotPage(snapshotPage - 1)}
                      disabled={snapshotPage <= 1}
                      className="h-9 px-4 text-xs font-semibold"
                    >
                      Anterior
                    </Button>
                    <div className="flex items-center gap-1 px-3 h-9 rounded-md bg-muted border border-border">
                      <span className="text-xs font-bold text-foreground">{snapshotPage}</span>
                      <span className="text-xs text-muted-foreground">de</span>
                      <span className="text-xs font-bold text-foreground">
                        {Math.ceil(snapshotTotal / snapshotPageSize)}
                      </span>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSnapshotPage(snapshotPage + 1)}
                      disabled={snapshotPage >= Math.ceil(snapshotTotal / snapshotPageSize)}
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

        {/* Create Primera Liquidacion Modal */}
        <LiquidacionEdificacionFormModal
          open={formOpen}
          onOpenChange={setFormOpen}
          onSuccess={handleFormSuccess}
        />

        {/* Nueva Revision Modal */}
        <NuevaRevisionFormModal
          liquidacionBase={nuevaRevisionBase}
          open={nuevaRevisionBase !== null}
          onOpenChange={(open) => !open && setNuevaRevisionBase(null)}
          onSuccess={handleNuevaRevisionSuccess}
        />
      </div>
    </div>
  );
}
