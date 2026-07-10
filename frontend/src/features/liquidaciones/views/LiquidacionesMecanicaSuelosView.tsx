/**
 * Vista para lista de Liquidaciones de Mecánica de Suelos.
 * Ruta: /liquidaciones/mecanica-suelos
 */
"use client";

import {
  ClipboardCheck,
  FileText,
  Hash,
  Home,
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
import { NuevaLiquidacionDropdown } from "../components/NuevaLiquidacionDropdown";
import { LiquidacionMecanicaSuelosCard } from "../components/LiquidacionMecanicaSuelosCard";
import { useLiquidacionesMecanicaSuelos } from "../hooks/useLiquidacionesMecanicaSuelos";
import type { LiquidacionCardBase } from "../types/liquidacion-general";

const KIND_ICON: LucideIcon = Scale;

interface LiquidacionesMecanicaSuelosViewProps {
  onSuccess?: () => void;
}

export function LiquidacionesMecanicaSuelosView({
  onSuccess,
}: LiquidacionesMecanicaSuelosViewProps) {
  const router = useRouter();
  const [searchInput, setSearchInput] = useState("");
  const [proyectoPublicId, setProyectoPublicId] = useState<string | null>(null);

  const {
    items: liquidationItems,
    total: liquidationTotal,
    page: liquidationPage,
    pageSize: liquidationPageSize,
    isLoading: isLiquidationLoading,
    isError: isLiquidationError,
    refetch: refetchLiquidations,
    setPage: setLiquidationPage,
  } = useLiquidacionesMecanicaSuelos({ page: 1, pageSize: 10 });

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
    router.push(`/liquidaciones/mecanica-suelos/${item.id}`);
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20">
              <KIND_ICON className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-black tracking-tight">Mecánica de Suelos</h1>
              <p className="text-sm text-muted-foreground">
                Liquidaciones de mecánica de suelos
              </p>
            </div>
          </div>
          <NuevaLiquidacionDropdown onSuccess={refetchLiquidations} />
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
                <NuevaLiquidacionDropdown onSuccess={refetchLiquidations} />
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {liquidationItems.map((item) => (
                  <LiquidacionMecanicaSuelosCard
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
    </div>
  );
}
