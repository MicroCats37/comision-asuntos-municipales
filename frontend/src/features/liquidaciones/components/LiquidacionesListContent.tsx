"use client";

import { Filter, type LucideIcon, Plus, X } from "lucide-react";
import { type ReactNode, Suspense, useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { useUrlViewMode } from "@/hooks/system/useUrlViewMode";
import { ConsultarIngenieroButton } from "../components/forms/ConsultarIngenieroButton";
import { LiquidacionFiltroModal } from "../components/forms/LiquidacionFiltroModal";
import { ViewModeToggle } from "../components/view-toggle/ViewModeToggle";
import { useLiquidacionFiltersUrl } from "../hooks/useLiquidacionFiltersUrl";
import type { LiquidacionFiltros } from "../hooks/useLiquidacionList";
import {
  LiquidacionesTable,
  type LiquidacionTableRow,
} from "./tables/LiquidacionesTable";

export interface UseLiquidacionListReturn<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  resetPagination: () => void;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

export interface LiquidacionesListContentProps<TItem> {
  icon: LucideIcon;
  title: string;
  description: string;
  /** "Nueva Liquidación" button (and other pre-filtros actions). */
  primaryAction?: ReactNode;
  /** Tertiary actions next to primary (e.g., "Tercera Revisión" for Edificaciones). */
  extraAction?: ReactNode;
  /** Hook bound to the domain-specific list fetcher. Reads URL state internally. */
  useListData: () => UseLiquidacionListReturn<TItem>;
  /** Renders a single card. Caller passes `refetch` for child "updated" hooks. */
  renderCard: (item: TItem, refetch: () => void) => ReactNode;
  /** Maps an item to the canonical row shape for Table view. */
  formatRow: (item: TItem) => LiquidacionTableRow;
  /** Optional per-row actions in Table view (e.g., "Ver detalle"). */
  renderRowActions?: (item: TItem) => ReactNode;
  /** Tipo-specific columns rendered contiguously between Comprobante and Subtotal. */
  extraColumns?: import("../components/tables/LiquidacionesTable").TableColumn<TItem>[];
}

function LiquidacionesListContentInner<TItem>({
  icon,
  title,
  description,
  primaryAction,
  extraAction,
  useListData,
  renderCard,
  formatRow,
  renderRowActions,
  extraColumns,
}: LiquidacionesListContentProps<TItem>) {
  const { filtros, setFiltros, clearFiltros } = useLiquidacionFiltersUrl();
  const [view] = useUrlViewMode();
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);

  const list = useListData();
  const activeFilterCount = Object.values(filtros).filter(Boolean).length;

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title={title}
          description={description}
          icon={icon}
          actionNodes={
            <>
              {primaryAction}
              <ConsultarIngenieroButton />
              {extraAction}
              <div className="ml-auto flex items-center gap-2 shrink-0">
                <ViewModeToggle />
                <Button
                  variant={activeFilterCount > 0 ? "default" : "outline"}
                  className="gap-2 h-10 rounded-xl font-semibold"
                  onClick={() => setFiltroModalOpen(true)}
                >
                  <Filter className="h-4 w-4" />
                  Filtros
                  {activeFilterCount > 0 && (
                    <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-primary-foreground/20 text-xs font-bold">
                      {activeFilterCount}
                    </span>
                  )}
                </Button>
              </div>
            </>
          }
        />

        <ActiveFiltersPanel
          filtros={filtros}
          onClear={() => {
            clearFiltros();
          }}
        />

        {list.isLoading ? (
          <ListSkeleton icon={icon} />
        ) : list.isError ? (
          <ListErrorMessage />
        ) : list.items.length === 0 ? (
          <ListEmptyState icon={icon} />
        ) : view === "table" ? (
          <>
            <LiquidacionesTable
              items={list.items}
              formatRow={formatRow}
              renderActions={renderRowActions}
              extraColumns={extraColumns}
            />
            <Pagination
              currentPage={list.page}
              totalPages={list.totalPages}
              totalItems={list.total}
              pageSize={list.pageSize}
              onPageChange={list.setPage}
              onPageSizeChange={list.setPageSize}
            />
          </>
        ) : (
          <>
            <div className="flex flex-col gap-3">
              {list.items.map((item) => (
                <div
                  key={
                    (item as { liquidacion_general?: { id?: string } })
                      .liquidacion_general?.id ?? Math.random().toString()
                  }
                >
                  {renderCard(item, list.refetch)}
                </div>
              ))}
            </div>
            <Pagination
              currentPage={list.page}
              totalPages={list.totalPages}
              totalItems={list.total}
              pageSize={list.pageSize}
              onPageChange={list.setPage}
              onPageSizeChange={list.setPageSize}
            />
          </>
        )}
      </div>

      <LiquidacionFiltroModal
        open={filtroModalOpen}
        onOpenChange={setFiltroModalOpen}
        initialFiltros={filtros}
        onApply={(next) => {
          setFiltros(next);
          setFiltroModalOpen(false);
        }}
      />
    </div>
  );
}

function ActiveFiltersPanel({
  filtros,
  onClear,
}: {
  filtros: LiquidacionFiltros;
  onClear: () => void;
}) {
  const activeFilterCount = Object.values(filtros).filter(Boolean).length;
  if (activeFilterCount === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/20 rounded-xl border border-border/60">
      <span className="text-xs font-semibold text-muted-foreground">
        Filtros activos:
      </span>
      {filtros.propietario && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Propietario: {filtros.propietario}
        </span>
      )}
      {filtros.razon_social && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Razón Social: {filtros.razon_social}
        </span>
      )}
      {filtros.entidad_id && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Municipalidad
        </span>
      )}
      {filtros.fecha_desde && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Desde: {filtros.fecha_desde}
        </span>
      )}
      {filtros.fecha_hasta && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Hasta: {filtros.fecha_hasta}
        </span>
      )}
      {filtros.creado_por && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Creado por: {filtros.creado_por}
        </span>
      )}
      {filtros.numero != null && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          N°: {filtros.numero}
        </span>
      )}
      {filtros.numero_revisiones != null && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Rev: {filtros.numero_revisiones}
        </span>
      )}
      {filtros.direccion && (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
          Dirección: {filtros.direccion}
        </span>
      )}
      <Button
        variant="ghost"
        size="sm"
        onClick={onClear}
        className="h-7 px-2 gap-1 text-xs text-destructive"
      >
        <X className="h-3 w-3" />
        Limpiar
      </Button>
    </div>
  );
}

function ListSkeleton({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-muted-foreground">
      <Icon className="h-6 w-6 animate-pulse opacity-50" />
      <div className="flex flex-col gap-3 w-full max-w-2xl">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-card rounded-xl border shadow-sm h-44 animate-pulse"
          />
        ))}
      </div>
    </div>
  );
}

function ListErrorMessage() {
  return (
    <div className="flex items-center justify-center p-8 text-destructive">
      Error al cargar las liquidaciones
    </div>
  );
}

function ListEmptyState({ icon: Icon }: { icon: LucideIcon }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
      <Icon className="h-10 w-10 text-muted-foreground mb-4" />
      <p className="text-muted-foreground">No hay liquidaciones registradas</p>
    </div>
  );
}

/**
 * Shared chrome for the 6 liquidacion listing pages. Encapsulates:
 * - URL-driven filter + pagination + view-mode state
 * - PageHeader with primary + filter actions
 * - Cards view, Table view toggle, skeletons, empty state, error message
 * - Pagination control
 *
 * Per-tipo views pass `useListData`, `renderCard`, and `formatRow` so the
 * chrome stays domain-agnostic. Form modals are kept as siblings in each
 * tipo-specific view (they're small and tipo-specific).
 *
 * Wrapped in `<Suspense>` for Next.js 16 because internal URL hooks use
 * `useSearchParams()`.
 */
export function LiquidacionesListContent<TItem>(
  props: LiquidacionesListContentProps<TItem>,
) {
  return (
    <Suspense fallback={<ListSkeleton icon={props.icon} />}>
      <LiquidacionesListContentInner {...props} />
    </Suspense>
  );
}

/** Default primary action button. Keeps callers terse. */
export function NuevaLiquidacionButton({
  onClick,
  children = "Nueva Liquidación",
}: {
  onClick: () => void;
  children?: ReactNode;
}) {
  return (
    <Button
      className="gap-2 h-10 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0"
      onClick={onClick}
    >
      <Plus className="h-4 w-4" />
      {children}
    </Button>
  );
}
