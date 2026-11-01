"use client";

/**
 * RhMensualCardShell — base visual COMÚN de las cards de RH mensual
 * (Inspector y Delegado).
 *
 * Sigue el patrón canónico de las cards de Liquidaciones
 * (`features/liquidaciones/components/cards/LiquidacionCardShell.tsx`):
 *
 *   <article> blanco + grid [main | summary 300px]
 *     main:     header (icono + título + badge N° RH + fecha de registro)
 *               identity-grid (Periodo | Persona | contexto del dominio)
 *               contenido específico del dominio (slot `children`)
 *     summary:  total a pagar + desglose secundario
 *     footer:   acciones (mismo orden, tamaño, iconos y política de texto)
 *
 * El shell NO conoce el dominio: las tablas de detalle, los bloques de
 * operatividad y los cálculos siguen siendo de cada card. Lo que se
 * homogeneiza aquí es la ESTRUCTURA, el ESPACIADO y las ACCIONES.
 */

import { Calendar, type LucideIcon, User } from "lucide-react";
import type { ReactNode } from "react";
import {
  formatCurrency,
  formatDate,
} from "@/features/liquidaciones/components/liquidacion-ui";
import { cn } from "@/lib/utils";

// ── Acciones ───────────────────────────────────────────────────────────────────

export interface RhCardAction {
  /** Clave estable para React. */
  key: string;
  icon: ReactNode;
  /** Texto visible — se oculta en pantallas pequeñas (`hidden sm:inline`). */
  label: string;
  /** Nombre accesible del botón (aria-label). */
  ariaLabel: string;
  onAction: () => void;
  variant?: "default" | "primary" | "danger";
  disabled?: boolean;
}

/**
 * Botón de acción de la card — mismas dimensiones (h-8 / px-3), mismo radio y
 * misma política de icono + texto en las dos cards de RH.
 */
function RhCardActionButton({ action }: { action: RhCardAction }) {
  return (
    <button
      type="button"
      onClick={action.onAction}
      disabled={action.disabled}
      aria-label={action.ariaLabel}
      title={action.ariaLabel}
      className={cn(
        "inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold transition-colors",
        "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
        action.variant === "primary" &&
          "border-primary/30 text-primary hover:bg-primary/10 hover:border-primary/50",
        action.variant === "danger" &&
          "border-destructive/40 text-destructive hover:bg-destructive/10 hover:border-destructive/60",
        (!action.variant || action.variant === "default") &&
          "border-border/60 text-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-primary",
      )}
    >
      {action.icon}
      <span className="hidden sm:inline">{action.label}</span>
    </button>
  );
}

// ── Resumen ───────────────────────────────────────────────────────────────────

export interface RhCardSummaryItem {
  label: string;
  value: string;
  tone?: "default" | "muted" | "danger";
}

/** Etiqueta del bloque de total (arriba a la derecha de la card). */
export interface RhCardPeriodo {
  periodo?: number | null;
  mes?: number | null;
}

// ── Shell ─────────────────────────────────────────────────────────────────────

export interface RhMensualCardShellProps {
  /** Icono del tipo de RH (Inspector / Delegado). */
  kindIcon: LucideIcon;
  /** Etiqueta del tipo: "Inspector" | "Delegado". */
  kindLabel: string;
  /** Título completo. Mantiene el título mensual por defecto. */
  title?: string;
  /** Número de RH de cabecera (puede venir null en históricos). */
  rhNumero?: number | null;
  /** Fecha de registro del RH (ISO). */
  fechaRegistro: string;
  /** Periodo del RH. */
  periodo: RhCardPeriodo;
  /** Periodo ya formateado para variantes no mensuales. */
  periodoLabel?: string;
  /** Nombre de la persona (inspector o delegado). */
  personaNombre?: string | null;
  /** Documento de la persona: "CIP: 12345" (puede incluir DNI). */
  personaDocumento?: string | null;
  /** Etiqueta e icono del segundo bloque de identidad. */
  identityLabel?: string;
  identityIcon?: LucideIcon;
  /** Etiqueta del total principal. Por defecto "Neto a pagar". */
  totalLabel?: string;
  /** Monto total del recibo. */
  total?: number | null;
  /** Desglose secundario del resumen (subtotal, descuento, tasas…). */
  summaryItems?: RhCardSummaryItem[];
  /**
   * Bloque contextual del dominio (p. ej. la operatividad del Delegado).
   * Se renderiza como tercera columna de la identity-grid.
   */
  contextSlot?: ReactNode;
  /** Acciones del recibo — el shell las renderiza en orden y con el mismo estilo. */
  actions: RhCardAction[];
  /** Contenido específico del dominio (tabla de detalle, resumen de inspecciones…). */
  children: ReactNode;
}

/**
 * Formatea el periodo del RH como `YYYY-MM` (o `—` si falta alguna parte).
 */
export function formatRhPeriodo({ periodo, mes }: RhCardPeriodo): string {
  if (periodo == null || mes == null) return "—";
  return `${periodo}-${String(mes).padStart(2, "0")}`;
}

export function RhMensualCardShell({
  kindIcon: KindIcon,
  kindLabel,
  title,
  rhNumero,
  fechaRegistro,
  periodo,
  periodoLabel: customPeriodoLabel,
  personaNombre,
  personaDocumento,
  identityLabel,
  identityIcon: IdentityIcon = User,
  totalLabel = "Neto a pagar",
  total,
  summaryItems = [],
  contextSlot,
  actions,
  children,
}: RhMensualCardShellProps) {
  const periodoLabel = customPeriodoLabel ?? formatRhPeriodo(periodo);

  return (
    <article className="bg-white border border-neutral-200 rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_300px] gap-5">
        {/* ── card-main ── */}
        <div className="min-w-0">
          {/* card-header */}
          <div className="flex flex-wrap items-start justify-between gap-3 pb-3.5 border-b border-neutral-200">
            <div className="flex gap-2.5 min-w-0">
              <div
                className="shrink-0 flex items-center justify-center rounded-xl"
                style={{
                  width: "39px",
                  height: "39px",
                  backgroundColor: "#f8e7e6",
                  border: "1px solid #edbfc1",
                  color: "#a90c24",
                }}
              >
                <KindIcon className="h-4 w-4" strokeWidth={1.7} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center flex-wrap gap-2">
                  <h2 className="m-0 text-base font-extrabold text-neutral-900 truncate">
                    {title ?? `Recibo de Honorario Mensual — ${kindLabel}`}
                  </h2>
                  {rhNumero != null && (
                    <span
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-bold"
                      style={{
                        color: "#a90c24",
                        backgroundColor: "#f8e7e6",
                        border: "1px solid #e6adb2",
                      }}
                      title={`Número de RH #${rhNumero}`}
                    >
                      N° {rhNumero}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-neutral-500 flex items-center gap-2.5">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {formatDate(fechaRegistro)}
                  </span>
                </p>
              </div>
            </div>
          </div>

          {/* identity-grid */}
          <div
            className={cn(
              "grid gap-2 mt-3.5",
              contextSlot
                ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
                : "grid-cols-1 sm:grid-cols-2",
            )}
          >
            {/* Periodo */}
            <section
              className="bg-white rounded-xl p-3 min-w-0"
              style={{
                border: "1px solid #eadedf",
                boxShadow: "inset 3px 0 0 #dca0a5",
              }}
            >
              <span
                className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider mb-2"
                style={{ color: "#a90c24" }}
              >
                <Calendar className="h-3 w-3" />
                Periodo
              </span>
              <strong className="block text-[13px] font-bold text-neutral-900 truncate">
                {periodoLabel}
              </strong>
            </section>

            {/* Persona (inspector o delegado) */}
            <section
              className="bg-white rounded-xl p-3 min-w-0"
              style={{
                border: "1px solid #eadedf",
                boxShadow: "inset 3px 0 0 #a90c24",
              }}
            >
              <span
                className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider mb-2"
                style={{ color: "#a90c24" }}
              >
                <IdentityIcon className="h-3 w-3" />
                {identityLabel ?? kindLabel}
              </span>
              <strong className="block text-[13px] font-bold text-neutral-900 truncate">
                {personaNombre || "—"}
              </strong>
              {personaDocumento && (
                <span className="flex items-center gap-1 text-[11px] mt-1.5 truncate text-neutral-500">
                  {personaDocumento}
                </span>
              )}
            </section>

            {/* Contexto del dominio (slot) */}
            {contextSlot}
          </div>
        </div>

        {/* ── card-summary ── */}
        <aside className="flex flex-col justify-center gap-2.5">
          <div
            className="flex items-end self-stretch"
            style={{ color: "#a90c24" }}
          >
            <div className="flex flex-col">
              <small className="text-[9px] font-bold uppercase tracking-wider text-neutral-500">
                {totalLabel}
              </small>
              <strong
                className="text-2xl font-black leading-none"
                style={{ color: "#a90c24" }}
              >
                {formatCurrency(total ?? 0)}
              </strong>
            </div>
          </div>

          {summaryItems.length > 0 && (
            <div className="grid grid-cols-2 gap-px bg-neutral-200 border border-neutral-200 rounded-lg overflow-hidden">
              {summaryItems.map((item) => (
                <div key={item.label} className="bg-white text-center p-2.5">
                  <span className="block uppercase text-[10px] font-bold tracking-wider text-neutral-500">
                    {item.label}
                  </span>
                  <strong
                    className={cn(
                      "block text-base mt-1 font-bold text-neutral-900",
                      item.tone === "danger" && "text-destructive",
                      item.tone === "muted" && "text-neutral-500",
                    )}
                  >
                    {item.value}
                  </strong>
                </div>
              ))}
            </div>
          )}
        </aside>

        {/* ── Contenido específico del dominio (full-width) ── */}
        <div className="min-w-0" style={{ gridColumn: "1 / -1" }}>
          {children}
        </div>

        {/* ── card-footer (acciones) ── */}
        {actions.length > 0 && (
          <footer
            className="flex items-center justify-end gap-2 pt-3 mt-0.5"
            style={{
              gridColumn: "1 / -1",
              borderTop: "1px solid #e8e0df",
            }}
          >
            {actions.map((action) => (
              <RhCardActionButton key={action.key} action={action} />
            ))}
          </footer>
        )}
      </div>
    </article>
  );
}
