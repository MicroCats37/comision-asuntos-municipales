"use client";

import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RichEmptyStateProps {
  icon: ReactNode;
  iconBgColor?: string;
  iconTextColor?: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

/**
 * Rich empty state matching the legacy's distinctive style.
 * Includes:
 * - Circular icon wrapper with background
 * - Descriptive title
 * - Longer description
 * - Prominent CTA button
 */
export function RichEmptyState({
  icon,
  iconBgColor = "bg-white",
  iconTextColor = "text-muted-foreground",
  title,
  description,
  actionLabel,
  onAction,
  className,
}: RichEmptyStateProps) {
  return (
    <div
      className={cn(
        "bg-muted/30 border-2 border-dashed border-border/70 rounded-[40px] p-12 text-center",
        className,
      )}
    >
      {/* Circular icon wrapper */}
      <div
        className={cn(
          "p-6 rounded-[24px] w-20 h-20 flex items-center justify-center mx-auto mb-6 shadow-sm border border-border/50",
          iconBgColor,
        )}
      >
        <div className={cn("shrink-0", iconTextColor)}>{icon}</div>
      </div>

      {/* Title */}
      <h3 className="text-xl font-black text-foreground mb-2 tracking-tight">
        {title}
      </h3>

      {/* Description */}
      <p className="text-sm text-muted-foreground mb-8 font-medium max-w-xs mx-auto leading-relaxed">
        {description}
      </p>

      {/* CTA Button */}
      {actionLabel && onAction && (
        <Button
          className="bg-primary hover:bg-primary/90 text-primary-foreground font-black rounded-2xl h-12 px-8 shadow-xl shadow-primary/10 active:scale-95 transition-all"
          onClick={onAction}
        >
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
