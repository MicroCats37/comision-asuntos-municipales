"use client";

import {
  Building2,
  Calendar,
  CheckCircle2,
  FileDown,
  FilePenLine,
  MapPin,
  Receipt,
  Users,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import {
  CardActionsMenu,
  CardActionItem,
  LiquidacionCardAction,
  formatCurrency,
  formatDate,
  getEstadoBadgeClass,
} from "../liquidacion-ui";

/**
 * Data shape of the active comprobante used to render the meta + action labels.
 * Mirrors the subset of the comprobante object the shell renders.
 */
export interface LiquidacionCardComprobante {
  tipo_comprobante?: string | null;
  serie?: string | null;
  numero?: string | null;
}

/**
 * Shared condensed-row card shell used by ALL liquidacion list cards
 * (Edificaciones + the other 5 domains).
 *
 * This is the canonical "row" layout:
 * - Row 1 (CSS Grid): identity (icon + publicId + estado) | main (entidad +
 *   proyecto) | meta (expediente, fecha, municipalidad, distrito, cta,
 *   comprobante, legacy) | total
 * - Optional per-type `bodySlot` (compact type-specific metrics)
 * - Optional `delegadosSlot` (DelegadosListBySpecialty, grouped by specialty)
 * - Row 2: shared actions (Delegados, PDF, Editar, Comprobante, Ver detalle)
 *
 * NO Collapsible/accordion, NO page navigation. "Ver detalle" is wired by the
 * consumer to open the inline LiquidacionDetalleModal.
 */
export function LiquidacionCardShell({
  kindIcon: KindIcon,
  publicId,
  estado,
  entidadNombre,
  proyectoNombre,
  municipalidadLabel,
  distritoLabel,
  expediente,
  codigoCta,
  legacy,
  comprobanteActivo,
  total,
  subTotal,
  fechaRegistro,
  showDelegados = true,
  onDelegados,
  onPrint,
  canEdit = false,
  onEdit,
  onComprobante,
  onVerDetalle,
  bodySlot,
  valuesSlot,
  delegadosSlot,
  menuItems,
  primaryAction,
}: {
  kindIcon: LucideIcon;
  publicId: string;
  estado?: string | null;
  entidadNombre: string;
  proyectoNombre?: string | null;
  municipalidadLabel: string;
  distritoLabel?: string;
  expediente?: string | null;
  codigoCta?: string | null;
  legacy?: boolean;
  comprobanteActivo?: LiquidacionCardComprobante | null;
  total?: number;
  subTotal?: number | null;
  fechaRegistro: string;
  showDelegados?: boolean;
  onDelegados?: () => void;
  onPrint?: () => void;
  canEdit?: boolean;
  onEdit?: () => void;
  onComprobante?: () => void;
  onVerDetalle?: () => void;
  bodySlot?: ReactNode;
  valuesSlot?: ReactNode;
  delegadosSlot?: ReactNode;
  /** Pre-built action items rendered inside a DropdownMenu "Opciones". */
  menuItems?: CardActionItem[];
  /** Standalone primary action rendered outside the dropdown (e.g. "Ver detalle"). */
  primaryAction?: ReactNode;
}) {
  return (
    <div className="group bg-card rounded-2xl border shadow-sm hover:shadow-md hover:border-primary/20 transition-all duration-200 overflow-hidden">
      {/*
       * Desktop: 2-row layout
       * Row 1: [identity] [main] [meta] [total]
       * Row 2: [actions — aligned right]
       * Mobile: vertical stack, actions wrap below
       */}
      <div className="px-4 py-3.5 flex flex-col gap-3">
        {/* ── Row 1: identity + main + meta + total ── */}
        <div className="grid grid-cols-1 lg:grid-cols-[200px_minmax(0,1.8fr)_minmax(0,1fr)_auto] lg:items-start gap-3 lg:gap-4">
          {/* ── identity: icono + publicId + estado ── */}
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 group-hover:bg-primary/15 transition-colors">
              <KindIcon className="h-4.5 w-4.5 text-primary" />
            </div>
            <div className="flex flex-col gap-1 min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <h3
                  className="text-sm font-black text-foreground tracking-tight truncate"
                  title={publicId}
                >
                  {publicId}
                </h3>
                {estado === "PAGADO" && (
                  <span
                    className={cn(
                      "shrink-0 inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                      getEstadoBadgeClass(estado ?? ""),
                    )}
                  >
                    {estado}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* ── main: entidad + proyecto ── */}
          <div className="flex flex-col gap-1 min-w-0">
            <p
              className="text-xs font-semibold text-foreground leading-snug line-clamp-2"
              title={entidadNombre}
            >
              {entidadNombre}
            </p>
            <p
              className="text-xs text-muted-foreground leading-snug truncate"
              title={proyectoNombre ?? undefined}
            >
              {proyectoNombre}
            </p>
          </div>

          {/* ── meta: expediente, fecha, municipalidad, distrito, codigo_cta, comprobante, legacy ── */}
          <div className="flex flex-wrap content-start gap-x-4 gap-y-1 text-xs text-muted-foreground/70 leading-relaxed">
            {expediente && (
              <span className="font-mono text-[11px] shrink-0">
                Exp: {expediente}
              </span>
            )}
            <span className="flex items-center gap-1 shrink-0">
              <Calendar className="h-3 w-3" />
              {formatDate(fechaRegistro)}
            </span>
            <span
              className="flex items-center gap-1 min-w-0"
              title={municipalidadLabel}
            >
              <Building2 className="h-3 w-3 shrink-0" />
              <span className="break-words whitespace-normal">
                {municipalidadLabel}
              </span>
            </span>
            {distritoLabel && (
              <span
                className="flex items-center gap-1 min-w-0"
                title={distritoLabel}
              >
                <MapPin className="h-3 w-3 shrink-0" />
                <span className="break-words whitespace-normal">
                  {distritoLabel}
                </span>
              </span>
            )}
            {codigoCta && (
              <span className="font-mono text-[11px] shrink-0">
                CTA: {codigoCta}
              </span>
            )}
            {legacy !== undefined && (
              <span
                className={cn(
                  "shrink-0 font-semibold text-[11px]",
                  legacy ? "text-amber-600" : "text-emerald-600",
                )}
              >
                {legacy ? "Legacy" : "Actual"}
              </span>
            )}
            {comprobanteActivo ? (
              <span className="flex items-center gap-1 shrink-0 text-emerald-600">
                <CheckCircle2 className="h-3 w-3" />
                <span className="text-[11px] truncate">
                  {comprobanteActivo.tipo_comprobante}{" "}
                  {comprobanteActivo.serie}-{comprobanteActivo.numero}
                </span>
              </span>
            ) : (
              <span className="flex items-center gap-1 shrink-0 text-muted-foreground/40">
                <XCircle className="h-3 w-3" />
                <span className="text-[11px]">Sin comprob.</span>
              </span>
            )}
          </div>

          {/* ── total ── */}
          <div className="shrink-0">
            <div className="bg-primary/5 border border-primary/10 rounded-xl px-3 py-2 flex items-center gap-2">
              <div className="text-right">
                <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider leading-none mb-0.5">
                  Total
                </p>
                <p className="text-lg font-black text-primary tracking-tight leading-none">
                  {formatCurrency(total ?? 0)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ── valuesSlot: Subtotal + Total center block (optional) ── */}
        {valuesSlot && (
          <div className="border-t border-border/40 pt-2.5">{valuesSlot}</div>
        )}

        {/* ── bodySlot: per-type condensed metrics (optional) ── */}
        {bodySlot && (
          <div className="border-t border-border/40 pt-2.5">{bodySlot}</div>
        )}

        {/* ── Delegados (compact, grouped by specialty) ── */}
        {delegadosSlot && (
          <div className="border-t border-border/40 pt-2.5">{delegadosSlot}</div>
        )}

        {/* ── Row 2: actions — CardActionsMenu dropdown + standalone primary ── */}
        <div className="flex items-center justify-end sm:justify-end gap-1.5 shrink-0 pt-0.5 border-t border-border/40">
          {menuItems && primaryAction ? (
            <CardActionsMenu items={menuItems} primaryAction={primaryAction} />
          ) : (
            <>
              {showDelegados && onDelegados && (
                <LiquidacionCardAction
                  icon={<Users className="h-3 w-3" />}
                  label={<span className="hidden sm:inline">Delegados</span>}
                  onAction={onDelegados}
                />
              )}
              {onPrint && (
                <LiquidacionCardAction
                  icon={<FileDown className="h-3 w-3" />}
                  label={<span className="hidden sm:inline">PDF</span>}
                  onAction={onPrint}
                />
              )}
              {canEdit && onEdit && (
                <LiquidacionCardAction
                  icon={<FilePenLine className="h-3 w-3" />}
                  label={<span className="hidden sm:inline">Editar</span>}
                  onAction={onEdit}
                />
              )}
              {onComprobante && (
                <LiquidacionCardAction
                  icon={<Receipt className="h-3 w-3" />}
                  label={
                    <span className="hidden sm:inline">
                      {comprobanteActivo
                        ? "Reemplazar comprobante"
                        : "Agregar comprobante"}
                    </span>
                  }
                  onAction={onComprobante}
                />
              )}
              {onVerDetalle && (
                <LiquidacionCardAction
                  variant="primary"
                  label="Ver detalle"
                  onAction={onVerDetalle}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}