"use client";

import { CheckIcon, ChevronDownIcon, SearchIcon, X } from "lucide-react";
import type * as React from "react";
/**
 * SearchableSelect — accessible searchable dropdown.
 *
 * Simplified from v2 (removed @tanstack/react-virtual):
 * - Popover for the floating menu wrapper.
 * - Native overflow-y-auto scroll container for options.
 * - useDeferredValue to keep the search input responsive.
 * - Simple keyboard navigation (ArrowUp/Down, Enter, Escape).
 */
import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";

import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export interface SearchableSelectOption {
  value: string;
  label: string;
}

interface SearchableSelectProps {
  /** Unique id for accessibility */
  id: string;
  /** Label displayed above the trigger (or used for aria-label when showLabel is false) */
  label: string;
  /** Currently selected value */
  value: string | null;
  /** Callback when a value is selected */
  onValueChange: (value: string | null) => void;
  /** All available options */
  options: SearchableSelectOption[];
  /** Placeholder when nothing is selected */
  placeholder?: string;
  /** Additional class for the root container */
  className?: string;
  /** Icon to show in the trigger */
  icon?: React.ElementType;
  /** Disable the control */
  disabled?: boolean;
  /** Error state for border styling */
  error?: boolean;
  /** Error message to display below the trigger */
  errorMessage?: string;
  /** Whether to render the visible Label. Defaults to true. Set false when used inside GenericInput wrapper. */
  showLabel?: boolean;
  /** Hides the error message text but keeps border styling. Use when GenericInput's FieldWrapper renders the error. Defaults to false. */
  hideErrorMessage?: boolean;
}

export function SearchableSelect({
  id,
  label,
  value,
  onValueChange,
  options,
  placeholder = "Buscar...",
  className,
  icon: Icon,
  disabled = false,
  error = false,
  errorMessage,
  showLabel = true,
  hideErrorMessage = false,
}: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  // Defer the search term so typing never freezes during heavy filtering
  const deferredSearch = useDeferredValue(search);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Find the selected option label
  const selectedOption = useMemo(
    () => options.find((opt) => opt.value === value),
    [options, value],
  );

  // Filter options by deferred search term (case-insensitive)
  const filteredOptions = useMemo(() => {
    const s = deferredSearch.trim().toLowerCase();
    if (!s) return options;
    return options.filter((opt) => opt.label.toLowerCase().includes(s));
  }, [options, deferredSearch]);

  // Reset search when popover closes
  useEffect(() => {
    if (!open) {
      setSearch("");
      setHighlightedIndex(-1);
    }
  }, [open]);

  // Focus input when popover opens
  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  // Scroll highlighted option into view
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll("[role='option']");
      items[highlightedIndex]?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightedIndex]);

  // Simple keyboard navigation
  function handleKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (!open) return;
    if (filteredOptions.length === 0) return;

    switch (e.key) {
      case "ArrowDown": {
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < filteredOptions.length - 1 ? prev + 1 : 0,
        );
        break;
      }
      case "ArrowUp": {
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev > 0 ? prev - 1 : filteredOptions.length - 1,
        );
        break;
      }
      case "Enter": {
        e.preventDefault();
        if (highlightedIndex >= 0 && filteredOptions[highlightedIndex]) {
          onValueChange(filteredOptions[highlightedIndex].value);
          setOpen(false);
        }
        break;
      }
      case "Escape": {
        e.preventDefault();
        setOpen(false);
        break;
      }
    }
  }

  return (
    <div className={cn("space-y-1.5", className)}>
      {showLabel && (
        <Label
          htmlFor={id}
          className={cn(
            "text-sm font-medium",
            error ? "text-destructive" : "text-primary",
          )}
        >
          {label}
        </Label>
      )}

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            id={id}
            type="button"
            disabled={disabled}
            onClick={() => setOpen(true)}
            className={cn(
              "relative flex w-fit min-w-0 shrink-0 items-center gap-2 rounded-lg border bg-background py-2 pr-3 pl-10 text-sm transition-all duration-200 overflow-hidden",
              "hover:shadow-sm",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2",
              "disabled:cursor-not-allowed disabled:opacity-50",
              // Border colors: normal, hover, error
              error
                ? "border-destructive focus-visible:border-destructive"
                : "border-input hover:border-primary/50",
            )}
            style={{
              height: "var(--input-height, 40px)",
              justifyContent: "flex-start",
            }}
            aria-expanded={open}
            aria-haspopup="listbox"
            aria-invalid={error}
          >
            {Icon && (
              <span
                className={cn(
                  "absolute left-3 top-1/2 -translate-y-1/2 transition-colors duration-200 pointer-events-none z-10",
                  error ? "text-destructive" : "text-primary",
                )}
              >
                <Icon className="h-4 w-4" />
              </span>
            )}
            <span
              className={cn(
                "flex-1 text-left truncate",
                !selectedOption && "text-muted-foreground",
              )}
            >
              {selectedOption ? selectedOption.label : placeholder}
            </span>
            {selectedOption && (
              <X
                className="h-3.5 w-3.5 text-muted-foreground shrink-0 hover:text-foreground mr-1 cursor-pointer"
                onClick={(e) => {
                  e.stopPropagation();
                  onValueChange(null);
                }}
                aria-label="Limpiar selección"
              />
            )}
            <ChevronDownIcon className="h-4 w-4 text-muted-foreground shrink-0 pointer-events-none" />
          </button>
        </PopoverTrigger>

        <PopoverContent
          className="w-full max-w-[--radix-popover-trigger-width] p-0 overflow-hidden flex flex-col"
          align="start"
          side="bottom"
          sideOffset={4}
          collisionPadding={8}
          onKeyDown={handleKeyDown}
        >
          {/* Search input (Sticky at top) */}
          <div className="flex items-center gap-2 border-b border-border px-3 py-2 bg-popover z-10 shrink-0">
            <SearchIcon className="h-4 w-4 text-muted-foreground shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setHighlightedIndex(-1);
              }}
              placeholder="Buscar..."
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              aria-label={`Buscar en ${label}`}
              role="combobox"
              aria-expanded={open}
              aria-controls={`${id}-listbox`}
              aria-autocomplete="list"
            />
          </div>

          {/* Options list — simple scroll, no virtualization */}
          <div ref={listRef} className="w-full max-h-[240px] overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <p className="px-3 py-4 text-sm text-center text-muted-foreground">
                Sin resultados
              </p>
            ) : (
              filteredOptions.map((opt, index) => {
                const isSelected = opt.value === value;
                const isHighlighted = index === highlightedIndex;

                return (
                  <button
                    key={opt.value}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => {
                      onValueChange(opt.value);
                      setOpen(false);
                    }}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    className={cn(
                      "w-full flex items-center gap-2 px-3 text-sm text-left transition-colors",
                      "hover:bg-accent hover:text-accent-foreground",
                      "focus:bg-accent focus:text-accent-foreground focus:outline-none",
                      isSelected && "bg-accent/50",
                      isHighlighted && "bg-accent",
                    )}
                  >
                    <span className="flex-1 truncate">{opt.label}</span>
                    {isSelected && (
                      <CheckIcon className="h-4 w-4 text-primary shrink-0" />
                    )}
                  </button>
                );
              })
            )}
          </div>
        </PopoverContent>
      </Popover>
      {error && errorMessage && !hideErrorMessage && (
        <p className="text-sm text-destructive font-medium">{errorMessage}</p>
      )}
    </div>
  );
}
