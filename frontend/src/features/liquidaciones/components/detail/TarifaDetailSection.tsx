"use client";

import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { calculoGridCols } from "../../utils/calculoGridCols";
import { DetalleSection } from "./DetalleSection";

/**
 * One cell of the TarifaDetailSection param grid.
 * - `label` is the small uppercase caption.
 * - `value` is the rendered value (string, JSX chip, badge, etc.).
 */
export interface TarifaParam {
  label: string;
  value: ReactNode;
}

interface TarifaDetailSectionProps {
  /** Bold uppercase title rendered in the header strip. */
  title: string;
  /** Lucide icon rendered next to the title. */
  icon: LucideIcon;
  /** Optional counter next to the title (e.g. "4 delegados"). */
  badge?: ReactNode;
  /** Optional "Trámite" chip rendered above the params grid. */
  tramiteLabel?: string;
  /** Params rendered in a responsive CSS grid (`calculoGridCols(N)`). */
  params?: TarifaParam[];
  /** Text shown when `params` is empty/omitted. Defaults to a generic message. */
  emptyText?: string;
  /** Optional extra content rendered below the params grid
   *  (e.g. inspectores + registros_pago tables for IO). */
  children?: ReactNode;
  /** Outer grid track. Defaults to `lg:col-span-12` (full-width slot in the
   *  detail modal grid). */
  className?: string;
  /** Inner padding (default `p-0` so the params grid hugs the borders). */
  contentClassName?: string;
}

/**
 * TarifaDetailSection — unified "Tarifa / Detalle técnico" wrapper used by
 * every modal "Ver Detalle" section across the 6 liquidation tipos.
 *
 * Encapsulates the boilerplate that used to be copy-pasted in each
 * `LiquidacionDetalle<Domain>Section`:
 *   1. The `<DetalleSection>` header (icon + title + badge).
 *   2. The optional "Trámite" chip row.
 *   3. The responsive CSS grid of params (`calculoGridCols(N)`) so the cells
 *      stay homogeneous across the 3-to-5 fields each motor exposes.
 *   4. The optional fallback text when params are empty.
 *   5. The optional `children` slot for tablas adicionales (IO).
 *
 * The card face uses a similar wrapper (`CalculoDetail` +
 * `CalculoPorcentaje | CalculoM2 | CalculoVisitas`) which mirrors this
 * structure for the compact card layout — keep them visually consistent.
 */
export function TarifaDetailSection({
  title,
  icon,
  badge,
  tramiteLabel,
  params = [],
  emptyText = "Sin parámetros técnicos registrados.",
  children,
  className = "lg:col-span-12",
  contentClassName = "p-0",
}: TarifaDetailSectionProps) {
  const hasParams = params.length > 0;

  return (
    <DetalleSection
      title={title}
      icon={icon}
      badge={badge}
      className={className}
      contentClassName={contentClassName}
    >
      <div className="flex flex-col">
        {tramiteLabel ? (
          <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-border/40 bg-muted/10">
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              Trámite
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-md border border-border/60 bg-card px-2 py-1 text-xs font-medium text-foreground">
              {tramiteLabel}
            </span>
          </div>
        ) : null}

        {hasParams ? (
          <div
            className={cn(
              "grid items-stretch overflow-hidden rounded-none",
              calculoGridCols(params.length),
            )}
          >
            {params.map((p, i) => (
              <div
                key={p.label}
                className="px-4 py-3 flex flex-col justify-center min-w-0"
                style={{
                  borderLeft:
                    i === 0 ? "none" : "1px solid rgb(237 207 209 / 0.6)",
                }}
              >
                <span className="block uppercase text-[10px] font-bold tracking-wider text-muted-foreground leading-tight">
                  {p.label}
                </span>
                <strong className="block mt-1 text-sm font-bold text-neutral-900 leading-tight">
                  {p.value}
                </strong>
              </div>
            ))}
          </div>
        ) : (
          <p className="px-4 py-3 text-xs italic text-muted-foreground">
            {emptyText}
          </p>
        )}

        {children ? (
          <div className="flex flex-col gap-3 px-4 py-3 border-t border-border/40">
            {children}
          </div>
        ) : null}
      </div>
    </DetalleSection>
  );
}
