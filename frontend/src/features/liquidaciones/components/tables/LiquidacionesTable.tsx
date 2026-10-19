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
  /** Unique key used by React. */
  key: string;
  /** Header label (e.g. "% Liq.", "Valor de Obra"). */
  header: string;
  /** Renders the body cell for `item`. */
  render: (item: T) => ReactNode;
}

/** Width (in px) of the sticky "Acción" column. Applied as min-width on
 * the sticky `<th>`/`<td>` so the column never collapses below the
 * minimum needed by the 3x2 grid of buttons. */
export const LIQUIDACIONES_TABLE_COL_ACTIONS = 104;
/** Width (in px) of the sticky "ID" column. Applied as min-width on the
 * sticky cell so the truncated ID + PENDIENTE badge always fit. */
export const LIQUIDACIONES_TABLE_COL_ID = 180;

interface LiquidacionesTableProps<T> {
  items: T[];
  formatRow: (item: T) => LiquidacionTableRow;
  renderActions?: (item: T) => ReactNode;
  /** Tipo-specific columns rendered contiguously between Comprobante and Subtotal. */
  extraColumns?: TableColumn<T>[];
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
 * Table view with sticky cols (1=Acción, 2=ID) + drag-to-scroll + tipo-specific
 * columns injected via `extraColumns`.
 *
 * Architecture (matches `EventosAdminTable` in the
 * `semana-ingenieria-mayo-2026` reference project):
 *   - `<table>` HTML native with `border-collapse: separate`.
 *   - 3-layer scroll container: outer→flex-col→scroll→inner(min-w-max).
 *   - Sticky columns 1 & 2: `sticky left-0` on the two first `<th>`/`<td>`,
 *     with shadow under the sticky boundary.
 *   - Horizontal lines: `border-b border-border/40` on every `<tr>`.
 *   - Vertical lines: `border-r border-border/40` on every cell except
 *     the last in each row (matches shadcn UI table conventions).
 *   - No CSS Grid, no `divide-x`. Borders are explicit per cell so they
 *     are reliably visible against the bg-card background (the previous
 *     CSS Grid + `divide-x` failed because `bg-card` on the next cell
 *     covered the `border-left` from `divide-x`).
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

  if (items.length === 0) return null;

  return (
    <div className="rounded-2xl bg-card/90 border shadow-sm overflow-hidden">
      <div
        ref={scrollRef}
        className="overflow-auto cursor-grab"
        {...dragHandlers}
      >
        <div className="min-w-max">
          <table className="w-full caption-bottom text-sm">
            <thead className="sticky top-0 z-40 bg-table-header">
              <tr className="border-b-2 border-b-border text-[10px] font-bold uppercase tracking-wider text-foreground/85">
                {/* Sticky — Acción */}
                <th
                  className="sticky left-0 z-30 bg-table-header-sticky px-3 py-2.5 text-center border-r border-border/40 [text-wrap:balance]"
                  style={{
                    width: `${LIQUIDACIONES_TABLE_COL_ACTIONS}px`,
                    minWidth: `${LIQUIDACIONES_TABLE_COL_ACTIONS}px`,
                    boxShadow: "4px 0 8px -2px rgb(0 0 0 / 0.06)",
                  }}
                >
                  Acción
                </th>
                {/* Sticky — ID */}
                <th
                  className="sticky z-20 bg-table-header-sticky px-3 py-2.5 border-r border-border/40 [text-wrap:balance]"
                  style={{
                    left: LIQUIDACIONES_TABLE_COL_ACTIONS,
                    width: `${LIQUIDACIONES_TABLE_COL_ID}px`,
                    minWidth: `${LIQUIDACIONES_TABLE_COL_ID}px`,
                    boxShadow: "4px 0 8px -2px rgb(0 0 0 / 0.06)",
                  }}
                >
                  ID
                </th>
                <th className="px-3 py-2.5 border-r border-border/40 [text-wrap:balance] text-center">
                  Rev.
                </th>
                <th className="px-3 py-2.5 border-r border-border/40 [text-wrap:balance]">
                  Entidad
                </th>
                <th className="px-3 py-2.5 border-r border-border/40 [text-wrap:balance]">
                  Administrado
                </th>
                <th className="px-3 py-2.5 border-r border-border/40 [text-wrap:balance]">
                  Proyecto
                </th>
                <th className="px-3 py-2.5 border-r border-border/40 [text-wrap:balance]">
                  Dirección
                </th>
                <th className="px-3 py-2.5 border-r border-border/40 [text-wrap:balance]">
                  Municipalidad
                </th>
                <th className="px-3 py-2.5 border-r border-border/40 [text-wrap:balance]">
                  Fecha
                </th>
                <th className="px-3 py-2.5 border-r border-border/40 [text-wrap:balance]">
                  Expediente
                </th>
                <th className="px-3 py-2.5 border-r border-border/40 [text-wrap:balance]">
                  Comprobante
                </th>
                {hasExtra &&
                  extraColumns?.map((col) => (
                    <th
                      key={col.key}
                      className="px-3 py-2.5 border-r border-border/40 [text-wrap:balance]"
                    >
                      {col.header}
                    </th>
                  ))}
                <th className="px-3 py-2.5 border-r border-border/40 text-right [text-wrap:balance]">
                  Subtotal
                </th>
                <th className="px-3 py-2.5 text-right [text-wrap:balance]">
                  Total
                </th>
              </tr>
            </thead>

            <tbody>
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
                  <tr
                    key={row.id}
                    className="bg-card transition-colors hover:bg-muted/30 border-b border-border/40"
                  >
                    {/* Sticky — Acción */}
                    <td
                      className="sticky left-0 z-30 bg-card px-3 py-3.5 border-r border-border/40"
                      style={{
                        width: `${LIQUIDACIONES_TABLE_COL_ACTIONS}px`,
                        minWidth: `${LIQUIDACIONES_TABLE_COL_ACTIONS}px`,
                        boxShadow: "4px 0 8px -2px rgb(0 0 0 / 0.06)",
                      }}
                    >
                      {renderActions?.(item)}
                    </td>

                    {/* Sticky — ID */}
                    <td
                      className="sticky z-20 bg-card px-3 py-3.5 border-r border-border/40 min-w-0"
                      style={{
                        left: LIQUIDACIONES_TABLE_COL_ACTIONS,
                        width: `${LIQUIDACIONES_TABLE_COL_ID}px`,
                        minWidth: `${LIQUIDACIONES_TABLE_COL_ID}px`,
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
                    </td>

                    {/* Revisión */}
                    <td className="px-3 py-3.5 border-r border-border/40">
                      <span className="inline-flex items-center justify-center min-w-[2.5rem] h-7 rounded-md bg-muted text-foreground/85 font-mono text-sm font-bold tabular-nums px-2">
                        {row.numeroRevision ?? (
                          <span className="text-muted-foreground/50 font-normal">
                            —
                          </span>
                        )}
                      </span>
                    </td>

                    {/* Entidad */}
                    <td className="px-3 py-3.5 border-r border-border/40 min-w-0">
                      <div className="flex flex-col gap-1">
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
                    </td>

                    {/* Administrado */}
                    <td className="px-3 py-3.5 border-r border-border/40 min-w-0">
                      <span className="text-sm text-foreground leading-snug [text-wrap:pretty]">
                        {row.administrado || (
                          <span className="text-muted-foreground/50">—</span>
                        )}
                      </span>
                    </td>

                    {/* Proyecto */}
                    <td className="px-3 py-3.5 border-r border-border/40 min-w-0">
                      <span className="text-xs text-muted-foreground leading-snug [text-wrap:pretty]">
                        {row.proyecto || (
                          <span className="text-muted-foreground/50">—</span>
                        )}
                      </span>
                    </td>

                    {/* Dirección */}
                    <td className="px-3 py-3.5 border-r border-border/40 min-w-0">
                      <div className="flex flex-col gap-0.5">
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
                    </td>

                    {/* Municipalidad */}
                    <td className="px-3 py-3.5 border-r border-border/40 min-w-0">
                      <div className="flex flex-col gap-1">
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
                    </td>

                    {/* Fecha */}
                    <td className="px-3 py-3.5 border-r border-border/40 text-xs text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="h-3 w-3 shrink-0" />
                        <span className="font-medium">
                          {formatDate(row.fecha)}
                        </span>
                      </div>
                    </td>

                    {/* Expediente */}
                    <td className="px-3 py-3.5 border-r border-border/40 min-w-0">
                      <span
                        className="font-mono text-[11px] text-muted-foreground truncate block"
                        title={row.expediente ?? undefined}
                      >
                        {row.expediente || (
                          <span className="text-muted-foreground/50">—</span>
                        )}
                      </span>
                    </td>

                    {/* Comprobante */}
                    <td className="px-3 py-3.5 border-r border-border/40 min-w-0">
                      <div className="flex flex-col gap-1">
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
                    </td>

                    {/* Tipo-specific extra columns */}
                    {hasExtra &&
                      extraColumns?.map((col) => (
                        <td
                          key={col.key}
                          className="px-0 py-0 border-r border-border/40"
                        >
                          {col.render(item)}
                        </td>
                      ))}

                    {/* Subtotal */}
                    <td className="px-3 py-3.5 border-r border-border/40">
                      <span className="block text-right text-xs font-semibold text-muted-foreground whitespace-nowrap">
                        {formatCurrency(row.subTotal ?? 0)}
                      </span>
                    </td>

                    {/* Total */}
                    <td className="px-3 py-3.5">
                      <span className="block text-right text-base font-black text-primary tracking-tight whitespace-nowrap">
                        {formatCurrency(row.total ?? 0)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
