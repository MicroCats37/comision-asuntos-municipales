"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FilterChip } from "./FilterChip";

export interface FilterEntry<K extends string = string> {
  key: K;
  label: string;
  value: string;
}

interface ActiveFiltersPanelProps<K extends string = string> {
  entries: FilterEntry<K>[];
  onRemove: (key: K) => void;
  onClearAll: () => void;
}

/**
 * Generic container for active filter badges.
 * Caller builds the entries array with pre-formatted display values.
 * No data fetching inside — purely presentational.
 */
export function ActiveFiltersPanel<K extends string = string>({
  entries,
  onRemove,
  onClearAll,
}: ActiveFiltersPanelProps<K>) {
  if (entries.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/20 rounded-xl border border-border/60">
      <span className="text-xs font-semibold text-muted-foreground">
        Filtros activos:
      </span>
      {entries.map((entry) => (
        <FilterChip
          key={entry.key}
          label={entry.label}
          value={entry.value}
          onRemove={() => onRemove(entry.key)}
        />
      ))}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onClearAll}
        className="h-7 px-2 gap-1 text-xs text-destructive"
      >
        <X className="h-3 w-3" />
        Limpiar todo
      </Button>
    </div>
  );
}
