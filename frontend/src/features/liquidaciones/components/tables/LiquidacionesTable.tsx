"use client";

import { Calendar, Receipt } from "lucide-react";
import {
  type ReactNode,
  type PointerEvent as ReactPointerEvent,
  useRef,
} from "react";
import { cn } from "@/lib/utils";
import {
  formatCurrency,
  formatDate,
  getEstadoBadgeClass,
} from "../liquidacion-ui";

/**
 * Row shape for the base columns (Fase 6A + 6A.b + 6C).
 *
 * Tipo-specific columns (Fase 6B) are rendered via `extraColumns` below.
 */
export interface LiquidacionTableRow {
  id: string;
  publicId: string;
  estado?: string | null | undefined;
  /** Revision number (liquidacion_general.numero_revision). */
  numeroRevision?: number | null;
  entidad: string;
  entidadDocTipo?: string | null;
  entidadDocNumero?: string | null;
  administrado?: string | null;
  proyecto?: string | null;
  direccion?: string | null;
  urbanizacion?: string | null;
  municipalidadCodigo?: string | null;
  municipalidadNombre?: string;
  expediente?: string | null;
  fecha: string;
  comprobanteActivo?: {
    tipo_comprobante?: string | null;
    serie?: string | null;
    numero?: string | null;
  } | null;
  legacy?: boolean | undefined;
  subTotal?: number | null;
  total?: number | null;
}

/** Tipo-specific column descriptor — added between Comprobante and Subtotal. */
export interface TableColumn<T> {
  /** Unique key used to name the CSS Grid track. */
  key: string;
  /** Header label (e.g. "% Liq.", "Valor de Obra"). */
  header: string;
  /** Renders the body cell for `item`. */
  render: (item: T) => ReactNode;
  /** CSS track size. Default `minmax(120px, 1fr)`. */
  width?: string;
}

export const LIQUIDACIONES_TABLE_COL_ACTIONS = 160;
export const LIQUIDACIONES_TABLE_COL_ID = 200;
export const LIQUIDACIONES_TABLE_MIN_WIDTH = 1400;

interface LiquidacionesTableProps<T> {
  items: T[];
  formatRow: (item: T) => LiquidacionTableRow;
  renderActions?: (item: T) => ReactNode;
  /** Tipo-specific columns rendered contiguously between Comprobante and Subtotal. */
  extraColumns?: TableColumn<T>[];
}

const GRID_TEMPLATE_BASE = `[actions]${LIQUIDACIONES_TABLE_COL_ACTIONS}px [id]${LIQUIDACIONES_TABLE_COL_ID}px [rev]80px [entidad]minmax(220px,1.5fr) [administrado]minmax(160px,1fr) [proyecto]minmax(180px,1.2fr) [direccion]minmax(200px,1.1fr) [muni]minmax(180px,1.1fr) [fecha]130px [expediente]minmax(160px,0.9fr) [comprobante]minmax(180px,1fr)`;
const GRID_TEMPLATE_TAIL = `[subtotal]120px [total]120px`;

function buildExtraColsTemplate<T>(cols: TableColumn<T>[] | undefined): string {
  if (!cols || cols.length === 0) return "";
  return cols
    .map((c) => `[${c.key}]${c.width ?? "minmax(120px,1fr)"}`)
    .join(" ");
}

function buildGridTemplate<T>(cols: TableColumn<T>[] | undefined): string {
  const extras = buildExtraColsTemplate(cols);
  return extras
    ? `${GRID_TEMPLATE_BASE} ${extras} ${GRID_TEMPLATE_TAIL}`
    : `${GRID_TEMPLATE_BASE} ${GRID_TEMPLATE_TAIL}`;
}

// Drag-to-scroll hook — see Fase 6C / 7.
//
// KEY DECISIONS (Fase 7 fix — "tirón"):
//   1. NO React state during drag. State updates cause mid-drag re-renders
//      that manifest as visible "jerks" (cursor toggle, className swap).
//   2. NO `setPointerCapture` on pointerdown — only after the 4px
//      threshold is crossed. Capturing pointer from pointerdown creates
//      weird focus / hover state changes that feel like a tug.
//   3. Direct DOM mutation for cursor / user-select (no className
//      toggling) avoids any React render cycle.
function useDragScroll<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const dragStateRef = useRef<{
    pointerId: number;
    startX: number;
    startScrollLeft: number;
    thresholdPassed: boolean;
  } | null>(null);

  const onPointerDown = (e: ReactPointerEvent<T>) => {
    const target = e.target as HTMLElement;
    if (
      target.closest(
        'button, a, [role="button"], input, textarea, select, label, [data-no-drag]',
      )
    ) {
      return;
    }
    if (e.button !== 0) return;
    const el = ref.current;
    if (!el) return;
    // Just record state — don't capture yet (capture happens on first move
    // past the 4px threshold, so a regular click doesn't trigger any
    // side-effects).
    dragStateRef.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startScrollLeft: el.scrollLeft,
      thresholdPassed: false,
    };
  };

  const onPointerMove = (e: ReactPointerEvent<T>) => {
    const state = dragStateRef.current;
    if (!state || state.pointerId !== e.pointerId) return;
    const el = ref.current;
    if (!el) return;
    const delta = e.clientX - state.startX;

    if (!state.thresholdPassed && Math.abs(delta) > 4) {
      state.thresholdPassed = true;
      el.setPointerCapture(e.pointerId);
      el.style.cursor = "grabbing";
      el.style.userSelect = "none";
    }

    if (state.thresholdPassed) {
      e.preventDefault();
      el.scrollLeft = state.startScrollLeft - delta;
    }
  };

  const endDrag = (e: ReactPointerEvent<T>) => {
    const state = dragStateRef.current;
    if (!state || state.pointerId !== e.pointerId) return;
    const el = ref.current;
    if (el?.hasPointerCapture(e.pointerId)) {
      el.releasePointerCapture(e.pointerId);
    }
    if (el) {
      el.style.cursor = "";
      el.style.userSelect = "";
    }
    dragStateRef.current = null;
  };

  return {
    ref,
    handlers: {
      onPointerDown,
      onPointerMove,
      onPointerUp: endDrag,
      onPointerCancel: endDrag,
    },
  };
}

/**
 * Table view with CSS-grid + sticky cols + drag-to-scroll + tipo-specific
 * columns injected via `extraColumns`.
 *
 * Sticky behaviour:
 *   - Columns 1 (Acción) and 2 (ID) horizontally sticky (`left: …`).
 *   - Header row vertically sticky (`top: 0`).
 *
 * Drag-to-scroll: click-and-drag horizontally inside the table.
 *
 * Cell-level backgrounds: `bg-table-header` per cell — column labels stay
 * opaque across scroll even when sticky cells overlap.
 */
export function LiquidacionesTable<T>({
  items,
  formatRow,
  renderActions,
  extraColumns,
}: LiquidacionesTableProps<T>) {
  const { ref: scrollRef, handlers: dragHandlers } =
    useDragScroll<HTMLDivElement>();
  const hasExtra = Boolean(extraColumns && extraColumns.length > 0);
  const gridTemplate = buildGridTemplate(extraColumns);

  if (items.length === 0) return null;

  return (
    <div
      ref={scrollRef}
      className="bg-card rounded-xl border shadow-sm overflow-x-auto cursor-grab"
      {...dragHandlers}
    >
      <div className="min-w-[1700px] divide-y divide-foreground/20">
        {/* Header — sticky vertical, per-cell bg-table-header */}
        <div
          className="sticky top-0 z-40 grid items-stretch bg-table-header border-b-2 border-b-border text-[10px] font-bold uppercase tracking-wider text-foreground/85"
          style={{ gridTemplateColumns: gridTemplate }}
        >
          <span
            className="sticky left-0 z-30 bg-table-header-sticky px-2 py-2.5 text-center border-r border-border [text-wrap:balance]"
            style={{ boxShadow: "inset -1px 0 0 var(--border)" }}
          >
            Acción
          </span>
          <span
            className="sticky z-20 bg-table-header-sticky px-3 py-2.5 border-r border-border [text-wrap:balance]"
            style={{
              left: LIQUIDACIONES_TABLE_COL_ACTIONS,
              boxShadow: "4px 0 8px -2px rgb(0 0 0 / 0.06)",
            }}
          >
            ID
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance] text-center">
            Rev.
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            Entidad
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            Administrado
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            Proyecto
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            Dirección
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            Municipalidad
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            Fecha
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            Expediente
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            Comprobante
          </span>
          {hasExtra &&
            extraColumns?.map((col) => (
              <span
                key={col.key}
                className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]"
              >
                {col.header}
              </span>
            ))}
          <span className="bg-table-header px-3 py-2.5 border-r border-border text-right [text-wrap:balance]">
            Subtotal
          </span>
          <span className="bg-table-header px-3 py-2.5 text-right [text-wrap:balance]">
            Total
          </span>
        </div>

        {/* Body rows */}
        {items.map((item) => {
          const row = formatRow(item);
          const docLabel =
            row.entidadDocTipo && row.entidadDocNumero
              ? {
                  tipo: row.entidadDocTipo,
                  numero: row.entidadDocNumero,
                }
              : null;
          const hasComprobante =
            row.comprobanteActivo !== null &&
            row.comprobanteActivo !== undefined;
          return (
            <div
              key={row.id}
              className="grid items-stretch bg-card transition-colors hover:bg-muted/30 divide-x divide-foreground/20"
              style={{ gridTemplateColumns: gridTemplate }}
            >
              {/* Sticky — Acción */}
              <div
                className="sticky left-0 z-30 flex items-center justify-center bg-card px-2 py-3.5 border-r border-border"
                style={{ boxShadow: "inset -1px 0 0 var(--border)" }}
              >
                {renderActions?.(item)}
              </div>

              {/* Sticky — ID */}
              <div
                className="sticky z-20 flex flex-col gap-1 bg-card px-3 py-3.5 border-r border-border min-w-0"
                style={{
                  left: LIQUIDACIONES_TABLE_COL_ACTIONS,
                  boxShadow: "4px 0 8px -2px rgb(0 0 0 / 0.06)",
                }}
              >
                <div className="flex items-center gap-2 flex-wrap min-w-0">
                  <span
                    className="font-mono text-sm font-bold tracking-tight truncate"
                    title={row.publicId}
                  >
                    {row.publicId}
                  </span>
                  {row.estado && (
                    <span
                      className={cn(
                        "inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                        getEstadoBadgeClass(row.estado),
                      )}
                    >
                      {row.estado}
                    </span>
                  )}
                </div>
              </div>

              {/* Revisión */}
              <div className="flex items-center justify-center px-3 py-3.5">
                <span className="inline-flex items-center justify-center min-w-[2.5rem] h-7 rounded-md bg-muted text-foreground/85 font-mono text-sm font-bold tabular-nums px-2">
                  {row.numeroRevision ?? (
                    <span className="text-muted-foreground/50 font-normal">
                      —
                    </span>
                  )}
                </span>
              </div>

              {/* Entidad */}
              <div className="flex flex-col justify-center gap-1 px-3 py-3.5 min-w-0">
                <span className="text-sm font-semibold leading-snug [text-wrap:pretty]">
                  {row.entidad}
                </span>
                {docLabel && (
                  <span className="inline-flex w-fit items-center gap-1 rounded-md bg-secondary px-1.5 py-0.5 text-[10px] tracking-wide">
                    <span className="font-bold text-secondary-foreground/80 uppercase">
                      {docLabel.tipo}
                    </span>
                    <span className="font-mono font-bold text-secondary-foreground">
                      {docLabel.numero}
                    </span>
                  </span>
                )}
              </div>

              {/* Administrado */}
              <div className="flex flex-col justify-center px-3 py-3.5 min-w-0">
                <span className="text-sm text-foreground leading-snug [text-wrap:pretty]">
                  {row.administrado || (
                    <span className="text-muted-foreground/50">—</span>
                  )}
                </span>
              </div>

              {/* Proyecto */}
              <div className="flex flex-col justify-center px-3 py-3.5 min-w-0">
                <span className="text-xs text-muted-foreground leading-snug [text-wrap:pretty]">
                  {row.proyecto || (
                    <span className="text-muted-foreground/50">—</span>
                  )}
                </span>
              </div>

              {/* Dirección */}
              <div className="flex flex-col gap-0.5 justify-center px-3 py-3.5 min-w-0">
                <span className="text-xs leading-snug [text-wrap:pretty]">
                  {row.direccion || (
                    <span className="text-muted-foreground/50">—</span>
                  )}
                </span>
                {row.urbanizacion && (
                  <span className="text-[10px] text-muted-foreground/70 italic leading-snug">
                    Urb. {row.urbanizacion}
                  </span>
                )}
              </div>

              {/* Municipalidad */}
              <div className="flex flex-col gap-1 justify-center px-3 py-3.5 min-w-0">
                {row.municipalidadCodigo && (
                  <span className="inline-flex w-fit items-center rounded-md bg-primary/10 text-primary px-1.5 py-0.5 text-[10px] font-bold tracking-wide">
                    {row.municipalidadCodigo}
                  </span>
                )}
                <span className="text-xs leading-snug [text-wrap:pretty]">
                  {row.municipalidadNombre || (
                    <span className="text-muted-foreground/50">—</span>
                  )}
                </span>
              </div>

              {/* Fecha */}
              <div className="flex items-center gap-1.5 px-3 py-3.5 text-xs text-muted-foreground">
                <Calendar className="h-3 w-3 shrink-0" />
                <span className="font-medium">{formatDate(row.fecha)}</span>
              </div>

              {/* Expediente */}
              <div className="flex items-center px-3 py-3.5 min-w-0">
                <span
                  className="font-mono text-[11px] text-muted-foreground truncate"
                  title={row.expediente ?? undefined}
                >
                  {row.expediente || (
                    <span className="text-muted-foreground/50">—</span>
                  )}
                </span>
              </div>

              {/* Comprobante */}
              <div className="flex flex-col gap-1 justify-center px-3 py-3.5 min-w-0">
                {hasComprobante && row.comprobanteActivo ? (
                  <span className="inline-flex items-center gap-1 text-success text-[11px] min-w-0">
                    <Receipt className="h-3 w-3 shrink-0" />
                    <span className="truncate">
                      {row.comprobanteActivo.tipo_comprobante}{" "}
                      {row.comprobanteActivo.serie}-
                      {row.comprobanteActivo.numero}
                    </span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-muted-foreground/50 text-[11px]">
                    <span className="h-2 w-2 rounded-full bg-muted-foreground/30" />
                    Sin comprob.
                  </span>
                )}
                {hasComprobante && row.legacy !== undefined && (
                  <span
                    className={cn(
                      "inline-flex w-fit items-center rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider",
                      row.legacy
                        ? "bg-warning/10 text-warning border-warning/20"
                        : "bg-success/10 text-success border-success/20",
                    )}
                  >
                    {row.legacy ? "Legacy" : "Actual"}
                  </span>
                )}
              </div>

              {/* Tipo-specific extra columns */}
              {hasExtra &&
                extraColumns?.map((col) => (
                  <div
                    key={col.key}
                    className="px-0 py-0 min-w-0 flex items-stretch"
                  >
                    {col.render(item)}
                  </div>
                ))}

              {/* Subtotal */}
              <div className="flex items-center justify-end px-3 py-3.5">
                <span className="text-xs font-semibold text-muted-foreground whitespace-nowrap">
                  {formatCurrency(row.subTotal ?? 0)}
                </span>
              </div>

              {/* Total */}
              <div className="flex items-center justify-end px-3 py-3.5">
                <span className="text-base font-black text-primary tracking-tight whitespace-nowrap">
                  {formatCurrency(row.total ?? 0)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
