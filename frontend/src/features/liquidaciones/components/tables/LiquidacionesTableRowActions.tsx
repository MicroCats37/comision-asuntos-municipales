"use client";

import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/**
 * One row-level action: an icon + label + handler.
 * Each action renders as an icon-only button with a tooltip on hover.
 */
export interface LiquidacionRowAction {
  /** Lucide icon for the button. */
  icon: LucideIcon;
  /** Tooltip text + accessibility label. */
  label: string;
  onAction: () => void;
  /** "primary" highlights the button. Defaults to ghost. */
  variant?: "default" | "primary";
  /** Hide the action without removing it from the caller's array. */
  hidden?: boolean;
}

/**
 * Inline icon-only action group for a Table row. Base component used by all
 * liquidacion list tables. Specific per-tipo actions are passed by the view.
 *
 * Pattern (mirrors LiquidacionCardShell + per-tipo card wrappers):
 *   - This is the BASE (visual chrome + tooltip + click handling).
 *   - Each view supplies the SPECIFIC action set (which buttons to show,
 *     which per-row state to read for `canEdit`, etc.).
 */
export function LiquidacionesTableRowActions({
  actions,
  size = "sm",
}: {
  actions: LiquidacionRowAction[];
  size?: "sm" | "xs";
}) {
  const visibleActions = actions.filter((a) => !a.hidden);
  if (visibleActions.length === 0) return null;

  const sizeClass = size === "xs" ? "h-6 w-6" : "h-7 w-7";
  const iconClass = size === "xs" ? "h-3 w-3" : "h-3.5 w-3.5";

  return (
    <div
      role="toolbar"
      aria-label="Acciones de la fila"
      className="flex items-center justify-end gap-0.5"
    >
      {visibleActions.map((action) => {
        const Icon = action.icon;
        const isPrimary = action.variant === "primary";
        return (
          <Tooltip key={action.label}>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant={isPrimary ? "default" : "ghost"}
                size="icon"
                aria-label={action.label}
                onClick={(e) => {
                  e.stopPropagation();
                  action.onAction();
                }}
                className={cn(
                  sizeClass,
                  isPrimary
                    ? "bg-primary/10 text-primary border border-primary/30 hover:bg-primary/20 hover:border-primary/50"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/60",
                )}
              >
                <Icon className={iconClass} />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top" sideOffset={4}>
              {action.label}
            </TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}
