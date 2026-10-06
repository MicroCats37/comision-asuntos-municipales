"use client";

import { CheckCircle2, Loader2, X } from "lucide-react";
import type { ReactNode } from "react";
import type { GenericModalSize } from "@/components/genericModal/GenericModal";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";

export type { GenericModalSize };

export interface ModalShellProps {
  /** Controlled open state */
  open: boolean;
  /** Callback fired when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Modal title */
  title: string;
  /** Optional description text below title */
  description?: string;
  /** Optional eyebrow label above title (e.g. "Editor de Reglas") */
  eyebrow?: string;
  /** Optional icon shown in the header block */
  icon?: ReactNode;
  /** Modal body content */
  children: ReactNode;
  /** Optional extra classes for the body wrapper */
  bodyClassName?: string;
  /** Label for the primary action button */
  primaryLabel: string;
  /** Override label shown while primary is loading */
  primaryLoadingLabel?: string;
  /** When true, primary button shows spinner and both buttons are disabled */
  primaryLoading?: boolean;
  /** Additional disabled state for primary button */
  primaryDisabled?: boolean;
  /** Called when primary button is clicked */
  onPrimary: () => void | Promise<void>;
  /** Label for the secondary/cancel button */
  secondaryLabel?: string;
  /** Called when secondary button is clicked */
  onSecondary?: () => void;
  /** Blocks closing via backdrop click or ESC when true */
  preventClose?: boolean;
  /** GenericModal size preset */
  size?: GenericModalSize;
}

export function ModalShell({
  open,
  onOpenChange,
  title,
  description,
  eyebrow,
  icon,
  children,
  bodyClassName,
  primaryLabel,
  primaryLoadingLabel,
  primaryLoading = false,
  primaryDisabled = false,
  onPrimary,
  secondaryLabel = "Cancelar",
  onSecondary,
  preventClose = false,
  size,
}: ModalShellProps) {
  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) {
      onOpenChange(false);
    }
  };

  return (
    <GenericModal
      open={open}
      onOpenChange={handleClose}
      preventClose={preventClose || primaryLoading}
    >
      <GenericModal.Content size={size}>
        {/* ── Header ─────────────────────────────────────────────── */}
        <GenericModal.Header
          title=""
          className="bg-primary/[0.03] border-b border-border px-6 py-5 sm:px-8"
        >
          {/* ── Icon + eyebrow + title + description row ─────────────── */}
          <div className="flex items-center gap-3 w-full">
            {/* Icon — small, inline, does not expand header */}
            {icon && (
              <div className="p-2 sm:p-2.5 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0 transition-transform duration-200 hover:scale-[1.02] active:scale-[0.98]">
                {icon}
              </div>
            )}
            {/* Eyebrow + title + description */}
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              {/* Eyebrow — compact, hidden on mobile */}
              {eyebrow && (
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  {eyebrow}
                </span>
              )}
              {/* Title — large, bold, strong */}
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                {title}
              </h2>
              {/* Description — hidden on mobile, constrained on desktop */}
              {description && (
                <p className="hidden sm:block max-w-prose text-pretty line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                  {description}
                </p>
              )}
            </div>
            {/* Spacer to mirror icon width */}
            {icon && (
              <div className="w-9 sm:w-11 shrink-0" aria-hidden="true" />
            )}
          </div>
        </GenericModal.Header>

        {/* ── Body ──────────────────────────────────────────────── */}
        <GenericModal.Body className={bodyClassName}>
          {children}
        </GenericModal.Body>

        {/* ── Footer ────────────────────────────────────────────── */}
        <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
          <div className="flex flex-row sm:justify-end items-center gap-2 sm:gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={onSecondary ?? (() => onOpenChange(false))}
              disabled={primaryLoading}
              className="flex-1 h-10 sm:h-11 rounded-xl font-semibold border border-border/60 hover:border-border hover:bg-background transition-all duration-200 sm:max-w-[120px] text-muted-foreground hover:text-foreground"
              aria-label={secondaryLabel}
            >
              <X className="h-4 w-4 sm:hidden" />
              <span className="hidden sm:inline">{secondaryLabel}</span>
            </Button>
            <Button
              type="button"
              onClick={onPrimary}
              disabled={primaryLoading || primaryDisabled}
              className="flex-1 h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2 sm:max-w-[160px] text-base transition-all duration-200 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 active:translate-y-0 disabled:hover:translate-y-0 disabled:hover:shadow-lg"
              aria-label={primaryLabel}
            >
              {primaryLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {!primaryLoading && (
                <CheckCircle2 className="h-4 w-4 sm:hidden" />
              )}
              <span className="hidden sm:inline">
                {primaryLoading
                  ? (primaryLoadingLabel ?? "Guardando...")
                  : primaryLabel}
              </span>
            </Button>
          </div>
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
