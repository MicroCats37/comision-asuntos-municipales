"use client";

import { X } from "lucide-react";

interface FilterChipProps {
  label: string;
  value: string;
  onRemove: () => void;
}

/**
 * Atom: single removable filter chip.
 * Caller provides already-formatted label and value strings.
 */
export function FilterChip({ label, value, onRemove }: FilterChipProps) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 pl-2.5 pr-1 py-1 text-xs font-medium">
      <span className="text-foreground/70 font-semibold">{label}:</span>
      <span className="font-bold">{value}</span>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Quitar filtro ${label}: ${value}`}
        className="inline-flex items-center justify-center h-5 w-5 rounded-full hover:bg-primary/20 text-primary transition-colors"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}
