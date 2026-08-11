"use client";

import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type FormSectionHeaderVariant = "soft" | "accent" | "plain";

interface FormSectionHeaderProps {
  title: string;
  icon?: LucideIcon;
  description?: string;
  variant?: FormSectionHeaderVariant;
  count?: number;
  countLabel?: string;
  className?: string;
}

/**
 * Reusable section header for forms.
 * Soft variant avoids the harsh `bg-primary text-primary-foreground` pattern.
 */
export function FormSectionHeader({
  title,
  icon: Icon,
  description,
  variant = "soft",
  count,
  countLabel,
  className,
}: FormSectionHeaderProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 -mx-4 -mt-4 px-4 py-3 rounded-t-xl border-b",
        {
          soft: "bg-primary/10 text-primary border-primary/20",
          accent: "bg-primary text-primary-foreground border-primary",
          plain: "bg-transparent text-foreground border-border",
        }[variant],
        className,
      )}
    >
      {Icon && <Icon className="h-4 w-4 shrink-0" />}
      <h3 className="text-sm font-semibold uppercase tracking-wide">{title}</h3>
      {count !== undefined && (
        <span className="ml-auto text-[10px] font-medium opacity-75">
          ({count} {countLabel ?? "seleccionado"}
          {count !== 1 ? "s" : ""})
        </span>
      )}
      {description && variant === "plain" && (
        <p className="text-xs text-muted-foreground ml-2">{description}</p>
      )}
    </div>
  );
}
