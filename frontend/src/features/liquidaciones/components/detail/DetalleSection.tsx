"use client";

import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface DetalleSectionProps {
  title: string;
  icon?: LucideIcon;
  children: ReactNode;
  badge?: ReactNode;
  contentClassName?: string;
  /** Tailwind class override for the outer section (e.g. `lg:col-span-12`). */
  className?: string;
}

/**
 * Base wrapper for each area of the Ver-Detalle modal. Card with a
 * header strip (icon + title + optional badge) and a content area.
 *
 * The outer section lives inside the modal body's 12-col CSS grid;
 * callers pass `className="lg:col-span-X"` to control width.
 */
export function DetalleSection({
  title,
  icon: Icon,
  badge,
  children,
  contentClassName,
  className,
}: DetalleSectionProps) {
  return (
    <section
      className={
        "rounded-xl border border-border/60 bg-card shadow-sm overflow-hidden " +
        (className ?? "")
      }
    >
      <header className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-border/40 bg-muted/30">
        <div className="flex items-center gap-2 min-w-0">
          {Icon ? (
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Icon className="h-3.5 w-3.5" />
            </span>
          ) : null}
          <h3 className="text-[11px] font-bold text-foreground uppercase tracking-wider truncate">
            {title}
          </h3>
          {badge != null ? (
            <span className="shrink-0 inline-flex items-center justify-center text-[10px] font-bold text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
              {badge}
            </span>
          ) : null}
        </div>
      </header>
      <div className={contentClassName ?? "p-4"}>{children}</div>
    </section>
  );
}

interface DetalleFieldProps {
  label: string;
  children: ReactNode;
  className?: string;
  mono?: boolean;
}

export function DetalleField({
  label,
  children,
  className,
  mono,
}: DetalleFieldProps) {
  return (
    <div className={`min-w-0 ${className ?? ""}`}>
      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
        {label}
      </p>
      <p
        className={
          (mono ? "font-mono tabular-nums " : "") +
          "text-sm text-foreground leading-snug break-words"
        }
      >
        {children}
      </p>
    </div>
  );
}
