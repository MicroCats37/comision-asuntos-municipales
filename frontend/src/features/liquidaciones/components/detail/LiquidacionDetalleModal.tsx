"use client";

import { FileText, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import type { GenericModalProps } from "@/components/genericModal/GenericModal.types";
import { cn } from "@/lib/utils";
import { getEstadoBadgeClass } from "../liquidacion-ui";

interface LiquidacionDetalleModalProps
  extends Pick<GenericModalProps, "open" | "onOpenChange"> {
  /** Badge text for the liquidacion type (e.g. "Edificacion") */
  kindBadge: string;
  /** Public identifier for the liquidacion (e.g. "EDIF-2026-054714") */
  publicId: string;
  /** Current estado of the liquidacion (e.g. "PAGADO", "PENDIENTE") */
  estado?: string | null;
  /** Optional icon for the kind badge */
  kindIcon?: LucideIcon;
  /** Slot for action buttons (e.g. PDF, Delegados) — rendered top-right of the header */
  actionsSlot?: ReactNode;
  /**
   * Body sections. Each child is a `<DetalleSection>` or similar.
   * They are stacked vertically inside the modal body with consistent
   * spacing. Subtotal + Total now live inside the `DetalleComercialSection`
   * — not in the header.
   */
  children: ReactNode;
}

const KindIconDefault = FileText;

/**
 * "Ver Detalle" modal — full redesign.
 *
 * Architecture:
 *   - Header: kind icon, publicId, kindBadge, estado badge, optional
 *     acciones, subtotal + total in a hero block.
 *   - Body: vertical stack of `<DetalleSection>` components. Each section
 *     is a self-contained card (Identidad, Proyecto, Tecnico tipo-specific,
 *     Comercial, Delegados, Contacto, Observacion). The view composes them.
 */
export function LiquidacionDetalleModal({
  open,
  onOpenChange,
  kindBadge,
  publicId,
  estado,
  kindIcon: KindIcon = KindIconDefault,
  actionsSlot,
  children,
}: LiquidacionDetalleModalProps) {
  return (
    <GenericModal open={open} onOpenChange={onOpenChange}>
      <GenericModal.Content className="flex flex-col max-h-[90vh]">
        {/* ── Header ─────────────────────────────────────────── */}
        <GenericModal.Header className="relative px-6 py-4 border-b border-border/60 bg-gradient-to-r from-muted/30 via-muted/10 to-transparent shrink-0">
          {/* CloseX */}
          <div className="absolute right-4 top-4 z-10">
            <GenericModal.CloseX />
          </div>

          <div className="flex items-start gap-3 pr-12">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
              <KindIcon className="h-5 w-5 text-primary" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-black text-foreground tracking-tight">
                  {publicId}
                </h2>
                {estado && (
                  <span
                    className={cn(
                      "shrink-0 inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                      getEstadoBadgeClass(estado),
                    )}
                  >
                    {estado}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-xs font-semibold text-secondary-foreground">
                  {kindBadge}
                </span>
              </div>
            </div>
          </div>

          {actionsSlot && (
            <div className="flex items-center gap-2 mt-4">{actionsSlot}</div>
          )}
        </GenericModal.Header>

        {/* ── Body ───────────────────────────────────────────── */}
        <GenericModal.Body className="flex-1 overflow-y-auto p-4 md:p-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mx-auto">
            {children}
          </div>
        </GenericModal.Body>
      </GenericModal.Content>
    </GenericModal>
  );
}
