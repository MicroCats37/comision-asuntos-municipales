"use client";

import { FileText, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import type { GenericModalProps } from "@/components/genericModal/GenericModal.types";
import { cn } from "@/lib/utils";
import { formatCurrency, getEstadoBadgeClass } from "../liquidacion-ui";

interface LiquidacionDetalleModalProps
  extends Pick<GenericModalProps, "open" | "onOpenChange"> {
  /** Badge text for the liquidacion type (e.g. "Edificación", "Mecánica de Suelos") */
  kindBadge: string;
  /** Public identifier for the liquidacion (e.g. "LIQ-2026-001234") */
  publicId: string;
  /** Current estado of the liquidacion (e.g. "PAGADO", "PENDIENTE") */
  estado?: string | null;
  /** Total a pagar — shown prominently in header and summary strip */
  total?: number;
  /** Optional icon for the kind badge */
  kindIcon?: LucideIcon;
  /** Slot for general section content */
  generalSection: ReactNode;
  /** Slot for specific section content (type-dependent) */
  especificoSection?: ReactNode;
  /** Slot for action buttons (e.g. PDF, Delegados) */
  actionsSlot?: ReactNode;
}

const KindIconDefault = FileText;

export function LiquidacionDetalleModal({
  open,
  onOpenChange,
  kindBadge,
  publicId,
  estado,
  total,
  kindIcon: KindIcon = KindIconDefault,
  generalSection,
  especificoSection,
  actionsSlot,
}: LiquidacionDetalleModalProps) {
  return (
    <GenericModal open={open} onOpenChange={onOpenChange}>
      <GenericModal.Content className="flex flex-col max-h-[90vh]">
        {/* ── Header ─────────────────────────────────────────── */}
        <GenericModal.Header className="relative px-6 py-4 border-b border-border/60 bg-gradient-to-r from-muted/30 via-muted/10 to-transparent shrink-0">
          {/* CloseX — absolute, top-right, clearly separated from content */}
          <div className="absolute right-4 top-4 z-10">
            <GenericModal.CloseX />
          </div>

          {/* Left zone: identity + status + kind */}
          <div className="flex items-start gap-3 pr-12">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20">
              <KindIcon className="h-5 w-5 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-black text-foreground tracking-tight">
                  {publicId}
                </h2>
                <span
                  className={cn(
                    "shrink-0 inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider",
                    getEstadoBadgeClass(estado ?? ""),
                  )}
                >
                  {estado ?? "—"}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary/60 border border-border/80 text-xs font-semibold text-secondary-foreground">
                  {kindBadge}
                </span>
              </div>
            </div>
          </div>

          {/* Right zone: total + actions, clearly separated from close button */}
          <div className="flex items-center justify-between gap-4 mt-3">
            <div className="flex items-center gap-2">{actionsSlot}</div>
            {total != null && (
              <div className="bg-primary/5 border border-primary/15 rounded-xl px-4 py-2 shrink-0">
                <p className="text-[9px] font-bold text-primary uppercase tracking-wider">
                  Total a Pagar
                </p>
                <p className="text-xl font-black text-primary tracking-tight">
                  {formatCurrency(total)}
                </p>
              </div>
            )}
          </div>
        </GenericModal.Header>

        {/* ── Body ───────────────────────────────────────────── */}
        <GenericModal.Body className="flex-1 overflow-y-auto p-0">
          <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-2">
            {/* General section — always shown */}
            <div className="min-w-0">{generalSection}</div>

            {/* Specific section — type-dependent */}
            {especificoSection && (
              <div className="min-w-0">{especificoSection}</div>
            )}
          </div>
        </GenericModal.Body>
      </GenericModal.Content>
    </GenericModal>
  );
}
