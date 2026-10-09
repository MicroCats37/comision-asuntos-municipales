/**
 * Vista para lista de filas sueltas de DetalleHonorarioDelegado (detalle flat).
 * Ruta: /liquidaciones/recibos-delegados/detalle
 *
 * Tabla CSS-grid con paginación y filtros URL-driven.
 * Filtros backend: delegado_id, periodo (opcional), mes (opcional),
 * municipalidad_id (opcional), tipo_liquidacion_codigo (REQUERIDO),
 * numero_liquidacion (opcional).
 *
 * El tipo de liquidación se selecciona mediante un segmented control (estilo
 * login de Mesa de Partes) — excluye INSPECCION_OBRA. Por defecto se activa
 * EDIFICACION al primer mount. El resto de filtros secundarios vive en el
 * modal de filtros y cada chip activo puede eliminarse individualmente.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import { Eye, Filter, RefreshCw, User, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { FilterChip } from "@/components/ui/active-filters";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { RHDetalleVerDetalleModal } from "@/features/finanzas/components/detail/RHDetalleVerDetalleModal";
import { RHDetalleDelegadosFiltroModal } from "@/features/finanzas/components/filtros";
import { RHDetalleDelegadosTable } from "@/features/finanzas/components/tables/RHDetalleDelegadosTable";
import type {
  DetalleDelegadoRow,
  RHDetalleRowAction,
} from "@/features/finanzas/components/tables/RHDetalleTable.types";
import { useRHDetalleDelegados } from "@/features/finanzas/hooks/useRHDetalleDelegados";
import { useRHDetalleDelegadosFiltersUrl } from "@/features/finanzas/hooks/useRHDetalleDelegadosFiltersUrl";
import { useMunicipalidades } from "@/features/liquidaciones/hooks/useMunicipalidades";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";
import { cn } from "@/lib/utils";

const KIND_ICON: LucideIcon = User;

/**
 * Tipos de liquidación disponibles como tabs (excluye INSPECCION_OBRA porque
 * ese flujo es exclusivo de inspectores, no de delegados).
 * El orden define el índice para el sliding indicator del segmented control.
 */
const TIPOS_LIQUIDACION_TABS: Array<{ codigo: string; label: string }> = [
  { codigo: "EDIFICACION", label: "Edificación" },
  { codigo: "HABILITACION_URBANA", label: "Habilitación Urbana" },
  { codigo: "MECANICA_SUELOS", label: "Mecánica de Suelos" },
  { codigo: "IMPACTO_VIAL", label: "Impacto Vial" },
  { codigo: "TALUDES", label: "Taludes" },
];

const DEFAULT_TIPO_CODIGO = TIPOS_LIQUIDACION_TABS[0].codigo;

export function RHDetalleDelegadosView() {
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);
  const [verDetalleId, setVerDetalleId] = useState<string | null>(null);

  const { page, pageSize, setPage, setPageSize } = useUrlPagination();
  const { filtros, setFiltros, clearFiltros } =
    useRHDetalleDelegadosFiltersUrl();

  // Default tab: EDIFICACION. Solo aplica en el primer mount si la URL no
  // trae un tipo_liquidacion_codigo — no pisa elecciones explícitas del usuario.
  // biome-ignore lint/correctness/useExhaustiveDependencies: intencional — solo primer mount.
  useEffect(() => {
    if (!filtros.tipo_liquidacion_codigo) {
      setFiltros({ ...filtros, tipo_liquidacion_codigo: DEFAULT_TIPO_CODIGO });
    }
  }, []);

  const { data: municipalidades = [] } = useMunicipalidades();
  const municipalidadNombreById = useMemo(() => {
    const map = new Map<string, string>();
    for (const m of municipalidades) {
      const codigoPrefix = m.codigo ? `${m.codigo} - ` : "";
      map.set(m.id, `${codigoPrefix}${m.nombre}`);
    }
    return map;
  }, [municipalidades]);

  const hasRequiredFilters = Boolean(filtros.tipo_liquidacion_codigo);

  const { items, total, totalPages, isLoading, isError, refetch } =
    useRHDetalleDelegados({
      page,
      pageSize,
      delegadoCip: filtros.delegado_cip,
      periodo: filtros.periodo,
      mes: filtros.mes,
      municipalidadId: filtros.municipalidad_id,
      tipoLiquidacionCodigo: filtros.tipo_liquidacion_codigo,
      numeroLiquidacion: filtros.numero_liquidacion,
      enabled: hasRequiredFilters,
    });

  const hasActiveFilters = Boolean(
    filtros.delegado_cip ||
      filtros.periodo ||
      filtros.mes ||
      filtros.municipalidad_id ||
      filtros.tipo_liquidacion_codigo ||
      filtros.numero_liquidacion,
  );

  const activeFilterCount = [
    filtros.delegado_cip,
    filtros.periodo,
    filtros.mes,
    filtros.municipalidad_id,
    filtros.tipo_liquidacion_codigo,
    filtros.numero_liquidacion,
  ].filter(Boolean).length;

  const renderActions = (item: DetalleDelegadoRow): RHDetalleRowAction[] => {
    const liquidacionId = item.delegado_liquidacion?.liquidacion?.id ?? null;
    return [
      {
        icon: Eye,
        label: "Ver detalle",
        variant: "primary",
        hidden: !liquidacionId,
        onAction: () => setVerDetalleId(liquidacionId),
      },
    ];
  };

  const handleTipoTabChange = (codigo: string) => {
    if (codigo === filtros.tipo_liquidacion_codigo) return;
    setFiltros({ ...filtros, tipo_liquidacion_codigo: codigo });
  };

  /**
   * Quita un único filtro del estado URL-driven. Mantiene el resto.
   * El tipo de liquidación se omite intencionalmente del chip removable —
   * siempre debe haber un tab activo (default o elegido).
   */
  const removeFilter = (key: keyof typeof filtros) => {
    const next = { ...filtros };
    delete next[key];
    setFiltros(next);
  };

  const showGuidedEmpty = !hasRequiredFilters && !isLoading;

  const activeTipoIndex = TIPOS_LIQUIDACION_TABS.findIndex(
    (t) => t.codigo === filtros.tipo_liquidacion_codigo,
  );

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Detalle de Honorarios - Delegados"
          description="Listado de filas detalle de recibos de honorarios de delegados"
          icon={KIND_ICON}
          actionNodes={
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
          }
        />

        {/* Segmented Control: tipo de liquidación (sin INSPECCION_OBRA).
            Estilo pill con sliding indicator inspirado en el login de Mesa
            de Partes. */}
        <div className="flex flex-col gap-3 p-4 bg-card rounded-2xl border border-border/60 shadow-sm">
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground ml-1">
            Tipo de liquidación
          </span>
          <div
            role="tablist"
            className="relative flex items-center w-full bg-muted/40 p-1 rounded-full shadow-[inset_0_1px_2px_oklch(0_0_0_/_0.06)] overflow-x-auto"
          >
            {activeTipoIndex >= 0 && (
              <div
                aria-hidden="true"
                className="absolute top-1 bottom-1 bg-primary rounded-full transition-all duration-300 ease-out shadow-[0_2px_8px_oklch(0.42_0.16_22_/_0.3)]"
                style={{
                  width: `calc(${100 / TIPOS_LIQUIDACION_TABS.length}% - 4px)`,
                  transform: `translateX(calc(${activeTipoIndex} * 100% + ${activeTipoIndex * 4}px))`,
                }}
              />
            )}

            {TIPOS_LIQUIDACION_TABS.map((t) => {
              const isActive = t.codigo === filtros.tipo_liquidacion_codigo;
              return (
                <button
                  key={t.codigo}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => handleTipoTabChange(t.codigo)}
                  className={cn(
                    "relative z-10 flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-full transition-all duration-300 whitespace-nowrap",
                    "text-[10px] sm:text-xs uppercase tracking-wider font-semibold",
                    isActive
                      ? "text-primary-foreground font-bold"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  <span>{t.label}</span>
                </button>
              );
            })}
          </div>
        </div>

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
            {filtros.numero_liquidacion && (
              <FilterChip
                label="N° Liquidación"
                value={String(filtros.numero_liquidacion)}
                onRemove={() => removeFilter("numero_liquidacion")}
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

        {/* Guided empty state cuando el filtro requerido falta */}
        {showGuidedEmpty && (
          <div className="border rounded-lg px-3 py-12 text-center">
            <p className="text-muted-foreground font-medium mb-1">
              Selecciona un tipo de liquidación para consultar
            </p>
            <p className="text-muted-foreground text-sm">
              El tipo de liquidación es el único filtro requerido. Usa las
              pestañas de arriba o aplica filtros adicionales desde el botón
              Filtros.
            </p>
          </div>
        )}
        {isLoading && (
          <div className="flex flex-col gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-card rounded-xl border shadow-sm h-16 animate-pulse"
              />
            ))}
          </div>
        )}
        {isError && (
          <div className="flex flex-col items-center justify-center p-8 text-destructive">
            <p className="font-medium mb-4">Error al cargar los datos</p>
            <Button variant="outline" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Reintentar
            </Button>
          </div>
        )}

        {!isLoading && !isError && (
          <>
            <RHDetalleDelegadosTable
              items={items}
              renderActions={renderActions}
            />

            {/* Empty state */}
            {items.length === 0 && (
              <div className="border rounded-lg px-3 py-8 text-center text-muted-foreground">
                No se encontraron filas detalle
              </div>
            )}

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

      {/* Ver detalle modal */}
      <RHDetalleVerDetalleModal
        liquidacionId={verDetalleId}
        open={verDetalleId !== null}
        onOpenChange={(open) => {
          if (!open) setVerDetalleId(null);
        }}
      />

      <RHDetalleDelegadosFiltroModal
        open={filtroModalOpen}
        onOpenChange={setFiltroModalOpen}
        initialFiltros={filtros}
        onApply={(nuevos) => {
          // CRITICAL: preservar tipo_liquidacion_codigo — el modal de filtros
          // NO incluye el tipo porque ya está seleccionado vía tabs.
          setFiltros({
            ...nuevos,
            tipo_liquidacion_codigo: filtros.tipo_liquidacion_codigo,
          });
          setFiltroModalOpen(false);
        }}
      />
    </div>
  );
}
