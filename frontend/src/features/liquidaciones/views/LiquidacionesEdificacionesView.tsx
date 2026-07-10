"use client";

import { FileText, Search, X } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  formatCurrency,
  LiquidacionGeneralCard,
} from "../components/LiquidacionGeneralCard";
import { NuevaLiquidacionDropdown } from "../components/NuevaLiquidacionDropdown";
import { useLiquidacionesEdificaciones } from "../hooks/useLiquidacionesEdificaciones";
import type { LiquidacionEdificacionOut } from "../types/liquidacion-edificaciones";
import type { LiquidacionCardBase, LiquidacionGeneralListItem } from "../types/liquidacion-general";

/** Format enum value to title case */
const formatEnumLabel = (value: string | null | undefined): string => {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

/** Full enum labels for better UX */
const getTipoTramiteLabel = (value: string | null | undefined): string => {
  switch (value) {
    case "OBRA_NUEVA":
      return "Obra Nueva";
    case "DEMOLICION":
      return "Demolición";
    case "AMPLIACION":
      return "Ampliación";
    case "REMODELACION":
      return "Remodelación";
    case "MODIFICACION_LICENCIA":
      return "Modificación de Licencia";
    default:
      return formatEnumLabel(value);
  }
};

const getTramiteAccionLabel = (value: string | null | undefined): string => {
  switch (value) {
    case "PRIMERA_REVISION":
      return "1ra. Revisión";
    case "REVISION":
      return "Revisión";
    default:
      return formatEnumLabel(value);
  }
};

/**
 * Edificación-specific summary block showing tipo_tramite, tramite_accion, revision.
 */
function EdificacionSummary({ item }: { item: LiquidacionEdificacionOut }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Tipo de Trámite
        </span>
        <span className="text-sm font-medium text-foreground">
          {getTipoTramiteLabel(item.tipo_tramite)}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Acción
        </span>
        <span className="text-sm font-medium text-foreground">
          {getTramiteAccionLabel(item.tramite_accion)}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Revisión
        </span>
        <span className="text-sm font-medium text-foreground">
          N° {item.numero_revision}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Expediente
        </span>
        <span className="text-sm font-medium text-foreground">
          {item.expediente || "—"}
        </span>
      </div>
    </div>
  );
}

/**
 * Edificación-specific values block showing valor_proyecto.
 */
function EdificacionValues({ item }: { item: LiquidacionEdificacionOut }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
        Valor del Proyecto
      </span>
      <span className="text-sm font-medium text-foreground">
        {formatCurrency(Number(item.proyecto.valor_proyecto))}
      </span>
    </div>
  );
}

/**
 * Vista de Liquidaciones de Edificaciones (list).
 * Muestra tarjetas con información resumida de cada liquidación.
 * Ruta: /liquidaciones/edificaciones
 *
 * @deprecated Use list/detail endpoints — this component uses the list
 *   endpoint (GET /liquidaciones/edificaciones) which returns basic info.
 *   For full detail (proyectistas, especialidades, totales), use the
 *   detail endpoint separately.
 */
export function LiquidacionesEdificacionesView() {
  const router = useRouter();
  const [searchInput, setSearchInput] = useState("");
  const [proyectoPublicId, setProyectoPublicId] = useState<string | null>(null);

  const {
    items: liquidacionItems,
    total: liquidacionTotal,
    page: liquidacionPage,
    pageSize: liquidacionPageSize,
    isLoading: isLiquidacionLoading,
    isError: isLiquidacionError,
    refetch: refetchLiquidaciones,
    setPage: setLiquidacionPage,
  } = useLiquidacionesEdificaciones({
    page: 1,
    pageSize: 10,
    proyectoPublicId,
  });

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
    router.push(`/liquidaciones/edificaciones/${item.id}`);
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
          <NuevaLiquidacionDropdown onSuccess={refetchLiquidaciones} />
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
                <NuevaLiquidacionDropdown onSuccess={refetchLiquidaciones} />
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {liquidacionItems.map((item) => (
                  <LiquidacionGeneralCard
                    key={item.id}
                    item={item as unknown as LiquidacionGeneralListItem}
                    onVerDetalle={handleVerDetalle}
                    typeSpecificSummary={<EdificacionSummary item={item} />}
                    typeSpecificValues={<EdificacionValues item={item} />}
                  />
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
    </div>
  );
}
