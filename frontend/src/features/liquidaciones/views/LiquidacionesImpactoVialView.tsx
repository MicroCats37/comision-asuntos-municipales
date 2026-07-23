/**
 * Vista para lista de Liquidaciones de Impacto Vial.
 * Ruta: /liquidaciones/impacto-vial
 */
"use client";

import {
  ClipboardCheck,
  FileText,
  Hash,
  Home,
  Plus,
  Scale,
  Search,
  Truck,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LiquidacionImpactoVialCard } from "../components/LiquidacionImpactoVialCard";
import { LiquidacionImpactoVialSingleFormModal } from "../components/LiquidacionImpactoVialSingleFormModal";
import { printImpactoVialDocument, type IVPrintData } from "../components/impacto-vial-print";
import { useLiquidacionesImpactoVial } from "../hooks/useLiquidacionesImpactoVial";
import type { LiquidacionCardBase } from "../types/liquidacion-general";
import type { CrearImpactoVialResponse } from "../types/liquidacion-impacto-vial.types";

const KIND_ICON: LucideIcon = Truck;

interface LiquidacionesImpactoVialViewProps {
  onSuccess?: () => void;
}

export function LiquidacionesImpactoVialView({
  onSuccess,
}: LiquidacionesImpactoVialViewProps) {
  const router = useRouter();
  const [searchInput, setSearchInput] = useState("");
  const [proyectoPublicId, setProyectoPublicId] = useState<string | null>(null);
  const [ivModalOpen, setIvModalOpen] = useState(false);

  const {
    items: liquidationItems,
    total: liquidationTotal,
    page: liquidationPage,
    pageSize: liquidationPageSize,
    isLoading: isLiquidationLoading,
    isError: isLiquidationError,
    refetch: refetchLiquidaciones,
    setPage: setLiquidationPage,
  } = useLiquidacionesImpactoVial({ page: 1, pageSize: 10 });

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

  const handleVerDetalle = (item: LiquidacionCardBase) => {
    router.push(`/liquidaciones/impacto-vial/${item.id}`);
  };

  const handleLiquidacionCreated = (created: CrearImpactoVialResponse) => {
    const printData: IVPrintData = {
      public_id: created.liquidacion.public_id,
      fecha_registro: created.liquidacion.fecha_creacion,
      expediente: created.liquidacion.expediente,
      municipalidad_codigo: null,
      municipalidad_nombre: "—",
      area_solicitada: 0,
      costo_por_m2: 0,
      derecho_minimo: 0,
      derecho_maximo: null,
      subtotal: created.totales.subtotal,
      igv: created.totales.igv,
      total: created.totales.total,
      liquidacion_total: created.totales.liquidacion_total,
      total_a_pagar: created.totales.total_a_pagar,
      proyecto_nombre: "—",
      proponente_nombre: "—",
    };

    void printImpactoVialDocument(printData);
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20">
              <KIND_ICON className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-black tracking-tight">Impacto Vial</h1>
              <p className="text-sm text-muted-foreground">
                Liquidaciones de impacto vial
              </p>
            </div>
          </div>
          <Button
            className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0"
            onClick={() => setIvModalOpen(true)}
          >
            <Plus className="h-4 w-4" />
            Nueva Liquidación
          </Button>
        </div>

        {/* Filter Bar */}
        <div className="flex items-center gap-4 p-4 bg-muted/20 rounded-xl border border-border/60">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-muted-foreground">
              Filtrar liquidaciones por ID de Proyecto:
            </span>
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
          {isLiquidationLoading ? (
            <div className="flex flex-col gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-card rounded-xl border shadow-sm h-48 animate-pulse"
                />
              ))}
            </div>
          ) : isLiquidationError ? (
            <div className="flex items-center justify-center p-8 text-destructive">
              Error al cargar las liquidaciones
            </div>
          ) : liquidationItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
              <KIND_ICON className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No hay liquidaciones registradas</p>
              <div className="mt-4">
                <Button
                  className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20"
                  onClick={() => setIvModalOpen(true)}
                >
                  <Plus className="h-4 w-4" />
                  Nueva Liquidación
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {liquidationItems.map((item) => (
                  <LiquidacionImpactoVialCard
                    key={item.id}
                    item={item}
                    onVerDetalle={handleVerDetalle}
                  />
                ))}
              </div>
              {liquidationTotal > liquidationPageSize && (
                <div className="flex items-center justify-between gap-4 pt-6 border-t border-border/50">
                  <span className="text-xs text-muted-foreground font-medium">
                    Mostrando {liquidationItems.length} de {liquidationTotal} liquidaciones
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setLiquidationPage(liquidationPage - 1)}
                      disabled={liquidationPage <= 1}
                      className="h-9 px-4 text-xs font-semibold"
                    >
                      Anterior
                    </Button>
                    <div className="flex items-center gap-1 px-3 h-9 rounded-md bg-muted border border-border">
                      <span className="text-xs font-bold text-foreground">{liquidationPage}</span>
                      <span className="text-xs text-muted-foreground">de</span>
                      <span className="text-xs font-bold text-foreground">
                        {Math.ceil(liquidationTotal / liquidationPageSize)}
                      </span>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setLiquidationPage(liquidationPage + 1)}
                      disabled={liquidationPage >= Math.ceil(liquidationTotal / liquidationPageSize)}
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

      <LiquidacionImpactoVialSingleFormModal
        open={ivModalOpen}
        onOpenChange={setIvModalOpen}
        onSuccess={refetchLiquidaciones}
        onCreated={handleLiquidacionCreated}
      />
    </div>
  );
}
