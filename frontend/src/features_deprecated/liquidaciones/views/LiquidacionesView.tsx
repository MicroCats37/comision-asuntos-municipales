"use client";

import { Building2, FileText, Plus, Search, UserCheck, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConsultarIngenieroDialog } from "../components/ConsultarIngenieroDialog";
import { LiquidacionListCard } from "../components/LiquidacionListCard";
import { NuevaRevisionEdificacionesFormModal } from "../components/NuevaRevisionEdificacionesFormModal";
import { LiquidacionStepperModal } from "../components/LiquidacionStepperModal";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { useLiquidacionesEdificaciones } from "../hooks/useLiquidacionesEdificaciones";
import type { LiquidacionEdificacionOut } from "../types/liquidacion-edificaciones";

/**
 * Vista genérica de Liquidaciones de Edificaciones (list).
 * Muestra tarjetas con información resumida de cada liquidación.
 *
 * @deprecated Use LiquidacionesEdificacionesView — this is a duplicate
 *   that was refactored to use non-snapshot list endpoint.
 */
export function LiquidacionesView() {
  const [searchInput, setSearchInput] = useState("");
  const [proyectoPublicId, setProyectoPublicId] = useState<string | null>(null);
  const [nuevaRevisionLiquidacionId, setNuevaRevisionLiquidacionId] = useState<string | null>(null);
  const [stepperOpen, setStepperOpen] = useState(false);
  const [consultDialogOpen, setConsultDialogOpen] = useState(false);

  const {
    items: liquidacionItems,
    total: liquidacionTotal,
    page: liquidacionPage,
    pageSize: liquidacionPageSize,
    isLoading: isLiquidacionLoading,
    isError: isLiquidacionError,
    refetch: refetchLiquidaciones,
    setPage: setLiquidacionPage,
  } = useLiquidacionesEdificaciones({ page: 1, pageSize: 10, proyectoPublicId });

  const handleSearch = () => {
    const trimmed = searchInput.trim();
    setProyectoPublicId(trimmed ? trimmed : null);
  };

  const handleClearFilter = () => {
    setSearchInput("");
    setProyectoPublicId(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        {/* Page Header */}
        <PageHeader
          title="Liquidaciones de Edificaciones"
          description="Gestiona las liquidaciones de proyectos de edificación"
          icon={Building2}
          actionNodes={
            <>
              <Button
                className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0"
                onClick={() => setStepperOpen(true)}
              >
                <Plus className="h-4 w-4" />
                Nueva Liquidación
              </Button>
              <Button
                variant="outline"
                className="gap-2 h-11 rounded-xl font-semibold shrink-0"
                onClick={() => setConsultDialogOpen(true)}
              >
                <UserCheck className="h-4 w-4" />
                Consultar ingeniero
              </Button>
            </>
          }
        />

        {/* Filter Bar */}
        <div className="flex items-center gap-4 p-4 bg-muted/20 rounded-xl border border-border/60">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-muted-foreground">Filtrar liquidaciones por ID de Proyecto:</span>
            <div className="flex items-center gap-2">
              <Input
                placeholder="Ej. PROY-2026-00001"
                aria-label="ID de proyecto público"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-[220px] h-9"
              />
              <Button
                variant="default"
                size="sm"
                onClick={handleSearch}
                className="h-9 px-3 gap-1"
              >
                <Search className="h-4 w-4" />
                Buscar
              </Button>
            </div>
          </div>
          {proyectoPublicId && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearFilter}
              className="h-8 px-2 gap-1 text-xs"
            >
              <X className="h-3 w-3" />
              Limpiar filtro
            </Button>
          )}
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
                <Button
                  className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20"
                  onClick={() => setStepperOpen(true)}
                >
                  <Plus className="h-4 w-4" />
                  Nueva Liquidación
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {liquidacionItems.map((item) => (
                  <LiquidacionListCard key={item.id} item={item} onNuevaRevision={(it) => setNuevaRevisionLiquidacionId(it.id)} />
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

      <NuevaRevisionEdificacionesFormModal
        open={!!nuevaRevisionLiquidacionId}
        onOpenChange={(open) => { if (!open) setNuevaRevisionLiquidacionId(null); }}
        liquidacionPreviaId={nuevaRevisionLiquidacionId}
        onSuccess={() => { setNuevaRevisionLiquidacionId(null); refetchLiquidaciones(); }}
      />

      <LiquidacionStepperModal
        open={stepperOpen}
        onOpenChange={setStepperOpen}
        onSuccess={refetchLiquidaciones}
      />

      <ConsultarIngenieroDialog
        open={consultDialogOpen}
        onOpenChange={setConsultDialogOpen}
      />
    </div>
  );
}
