"use client";

import { type PointerEvent as ReactPointerEvent, useRef } from "react";
import { cn } from "@/lib/utils";
import {
  formatCurrency,
  getKindBadgeFromCodigo,
} from "@/features/liquidaciones/components/liquidacion-ui";
import { LiquidacionesTableRowActions } from "@/features/liquidaciones/components/tables/LiquidacionesTableRowActions";
import type {
  DetalleDelegadoRow,
  RHDetalleDelegadoRow,
  RHDetalleRowAction,
} from "./RHDetalleTable.types";
import {
  formatDelegadoRow,
  RH_TABLE_COL_ACTIONS,
  RH_DELEGADOS_GRID_TEMPLATE,
} from "./RHDetalleTable.types";

interface RHDetalleDelegadosTableProps {
  items: DetalleDelegadoRow[];
  renderActions: (item: DetalleDelegadoRow) => RHDetalleRowAction[];
}

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
        "button, a, [role='button'], input, textarea, select, label, [data-no-drag]",
      )
    ) {
      return;
    }
    if (e.button !== 0) return;
    const el = ref.current;
    if (!el) return;
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
    handlers: { onPointerDown, onPointerMove, onPointerUp: endDrag, onPointerCancel: endDrag },
  };
}

/**
 * CSS-grid table for RH Detalle Delegados — mirrors the LiquidacionesTable architecture:
 * sticky Acción + ID columns, drag-to-scroll, row actions via LiquidacionesTableRowActions.
 *
 * Grid template:
 * [actions]160px [id]200px [expediente]minmax(160px,1fr) [delegado]minmax(200px,1.5fr)
 * [numero_rh]120px [periodo]120px [dictamen]120px [fecha_presentacion]120px [fecha_revision]120px [imp_bruto]120px [renta_cip]120px [aporte_codemu]120px [fondo_comun]120px [neto]120px
 */
export function RHDetalleDelegadosTable({
  items,
  renderActions,
}: RHDetalleDelegadosTableProps) {
  const { ref: scrollRef, handlers: dragHandlers } =
    useDragScroll<HTMLDivElement>();

  if (items.length === 0) return null;

  return (
    <div
      ref={scrollRef}
      className="bg-card rounded-xl border shadow-sm overflow-x-auto cursor-grab"
      {...dragHandlers}
    >
      <div className="min-w-[1500px] divide-y divide-foreground/20">
        {/* Header */}
        <div
          className="sticky top-0 z-40 grid items-stretch bg-table-header border-b-2 border-b-border text-[10px] font-bold uppercase tracking-wider text-foreground/85"
          style={{ gridTemplateColumns: RH_DELEGADOS_GRID_TEMPLATE }}
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
              left: RH_TABLE_COL_ACTIONS,
              boxShadow: "4px 0 8px -2px rgb(0 0 0 / 0.06)",
            }}
          >
            ID
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            N° RH
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            Expediente
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance]">
            Delegado
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance] text-center">
            Período
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance] text-center">
            Dictamen
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance] text-center">
            F. Presentación
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance] text-center">
            F. Revisión
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance] text-right">
            Imp. Bruto
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance] text-right">
            Renta CIP
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance] text-right">
            Aporte CODEMU
          </span>
          <span className="bg-table-header px-3 py-2.5 border-r border-border [text-wrap:balance] text-right">
            Fondo Común
          </span>
          <span className="bg-table-header px-3 py-2.5 text-right [text-wrap:balance]">
            Neto
          </span>
        </div>

        {/* Body rows */}
        {items.map((item) => {
          const row: RHDetalleDelegadoRow = formatDelegadoRow(item);
          const actions = renderActions(item);

          return (
            <div
              key={row.id}
              className="grid items-stretch bg-card transition-colors hover:bg-muted/30 divide-x divide-foreground/20"
              style={{ gridTemplateColumns: RH_DELEGADOS_GRID_TEMPLATE }}
            >
              {/* Sticky — Acción */}
              <div
                className="sticky left-0 z-30 flex items-center justify-center bg-card px-2 py-3.5 border-r border-border"
                style={{ boxShadow: "inset -1px 0 0 var(--border)" }}
              >
                <LiquidacionesTableRowActions actions={actions} size="sm" />
              </div>

              {/* Sticky — ID */}
              <div
                className="sticky z-20 flex flex-col gap-1 bg-card px-3 py-3.5 border-r border-border min-w-0"
                style={{
                  left: RH_TABLE_COL_ACTIONS,
                  boxShadow: "4px 0 8px -2px rgb(0 0 0 / 0.06)",
                }}
              >
                <div className="flex items-center gap-2 flex-wrap min-w-0">
                  <span className="font-mono text-sm font-bold tracking-tight truncate">
                    {row.numero ?? "—"}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap min-w-0">
                  {row.tipoCodigo ? (
                    <span
                      className={cn(
                        "shrink-0 inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                        getKindBadgeFromCodigo(row.tipoCodigo),
                      )}
                    >
                      {row.tipoCodigo}
                    </span>
                  ) : null}
                </div>
              </div>

              {/* N° RH */}
              <div className="flex items-center px-3 py-3.5 min-w-0">
                <span className="font-mono text-[11px] text-muted-foreground truncate">
                  {row.numeroRh || <span className="text-muted-foreground/50">—</span>}
                </span>
              </div>

              {/* Expediente */}
              <div className="flex items-center px-3 py-3.5 min-w-0">
                <span className="font-mono text-[11px] text-muted-foreground truncate">
                  {row.expediente || (
                    <span className="text-muted-foreground/50">—</span>
                  )}
                </span>
              </div>

              {/* Delegado */}
              <div className="flex flex-col justify-center gap-1 px-3 py-3.5 min-w-0">
                <span className="text-sm font-semibold leading-snug [text-wrap:pretty]">
                  {row.delegadoNombre || (
                    <span className="text-muted-foreground/50">—</span>
                  )}
                </span>
                {row.delegadoCip && (
                  <span className="inline-flex w-fit items-center rounded-md bg-secondary px-1.5 py-0.5 text-[10px] tracking-wide">
                    <span className="font-mono font-bold text-secondary-foreground">
                      CIP: {row.delegadoCip}
                    </span>
                  </span>
                )}
              </div>

              {/* Período */}
              <div className="flex flex-col items-center justify-center gap-0.5 px-3 py-3.5">
                <span className="inline-flex items-center justify-center min-w-[2.5rem] h-7 rounded-md bg-muted text-foreground/85 font-mono text-sm font-bold tabular-nums px-2">
                  {row.periodo && row.mes != null
                    ? `${row.periodo}/${String(row.mes).padStart(2, "0")}`
                    : "—"}
                </span>
              </div>

              {/* Dictamen */}
              <div className="flex items-center justify-center px-3 py-3.5">
                {row.dictamenRevision && (
                  <span
                    className={cn(
                      "shrink-0 inline-flex items-center rounded-full border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider",
                      row.dictamenRevision === "CONFORME"
                        ? "border-green-600 text-green-700 bg-green-50"
                        : row.dictamenRevision === "NO_CONFORME"
                          ? "border-red-600 text-red-700 bg-red-50"
                          : row.dictamenRevision === "PENDIENTE"
                            ? "border-yellow-600 text-yellow-700 bg-yellow-50"
                            : "border-blue-600 text-blue-700 bg-blue-50",
                    )}
                  >
                    {row.dictamenRevision.replace("_", " ")}
                  </span>
                )}
                {!row.dictamenRevision && (
                  <span className="text-muted-foreground/50">—</span>
                )}
              </div>

              {/* F. Presentación */}
              <div className="flex items-center justify-center px-3 py-3.5 text-center">
                <span className="font-mono text-[11px] font-semibold leading-none">
                  {row.fechaPresentacion?.slice(0, 10) ?? "—"}
                </span>
              </div>

              {/* F. Revisión */}
              <div className="flex items-center justify-center px-3 py-3.5 text-center">
                <span className="font-mono text-[11px] font-semibold leading-none">
                  {row.fechaRevision?.slice(0, 10) ?? "—"}
                </span>
              </div>

              {/* Imp. Bruto */}
              <div className="flex items-center justify-end px-3 py-3.5">
                <span className="text-xs font-semibold text-muted-foreground whitespace-nowrap">
                  {formatCurrency(row.impBruto ?? 0)}
                </span>
              </div>

              {/* Renta CIP */}
              <div className="flex items-center justify-end px-3 py-3.5">
                <span className="text-xs font-semibold text-muted-foreground whitespace-nowrap">
                  {formatCurrency(row.rentaCip ?? 0)}
                </span>
              </div>

              {/* Aporte CODEMU */}
              <div className="flex items-center justify-end px-3 py-3.5">
                <span className="text-xs font-semibold text-muted-foreground whitespace-nowrap">
                  {formatCurrency(row.aporteCodem ?? 0)}
                </span>
              </div>

              {/* Fondo Común */}
              <div className="flex items-center justify-end px-3 py-3.5">
                <span className="text-xs font-semibold text-muted-foreground whitespace-nowrap">
                  {formatCurrency(row.fondoComun ?? 0)}
                </span>
              </div>

              {/* Neto */}
              <div className="flex items-center justify-end px-3 py-3.5">
                <span className="text-base font-black text-primary tracking-tight whitespace-nowrap">
                  {formatCurrency(row.neto ?? 0)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
