"use client";

import { LayoutGrid, Table2 } from "lucide-react";
import { useUrlViewMode, type ViewMode } from "@/hooks/system/useUrlViewMode";
import { cn } from "@/lib/utils";

interface ViewModeToggleProps {
  className?: string;
}

/**
 * Segmented control between Card view and Table view. Default is "cards"
 * (URL keeps the param hidden when at default). Backed by `?view=table` so
 * the choice travels with shared links.
 */
export function ViewModeToggle({ className }: ViewModeToggleProps) {
  const [view, setView] = useUrlViewMode();

  const options: Array<{
    value: ViewMode;
    icon: typeof LayoutGrid;
    label: string;
  }> = [
    { value: "cards", icon: LayoutGrid, label: "Cards" },
    { value: "table", icon: Table2, label: "Tabla" },
  ];

  return (
    <div
      role="tablist"
      aria-label="Modo de visualización"
      className={cn(
        "inline-flex h-10 items-center gap-1 rounded-xl border border-border/60 bg-card p-1 shadow-sm",
        className,
      )}
    >
      {options.map(({ value, icon: Icon, label }) => {
        const active = view === value;
        return (
          <button
            type="button"
            key={value}
            role="tab"
            aria-selected={active}
            onClick={() => setView(value)}
            className={cn(
              "inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
              active
                ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        );
      })}
    </div>
  );
}
