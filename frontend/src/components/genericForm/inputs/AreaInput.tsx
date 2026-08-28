// AreaInput.tsx
"use client";

import type { LucideIcon } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Control, FieldPath, FieldValues } from "react-hook-form";
import { useController } from "react-hook-form";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface AreaInputProps<TFieldValues extends FieldValues = FieldValues> {
  /** Field name */
  name: FieldPath<TFieldValues>;
  /** Display label */
  label?: string;
  /** Icon component */
  icon?: LucideIcon;
  /** Placeholder text */
  placeholder?: string;
  /** Disabled state */
  disabled?: boolean;
  /** Required field */
  required?: boolean;
  /** Minimum value */
  min?: number;
  /** Additional CSS classes for the input element */
  className?: string;
  /** CSS classes for the container */
  containerClassName?: string;
  /** RHF error message */
  error?: { message?: string };
  /** RHF control */
  control: Control<TFieldValues>;
  /** Default value */
  defaultValue?: number | "";
  /** Called when Enter key is pressed */
  onEnter?: () => void;
}

/**
 * AreaInput — smart numeric input for area values (m²).
 *
 * Pattern (matches MoneyInput discipline):
 * - UI manages a STRING representation (displayValue)
 * - Internal logic handles formatting/parsing/conditions
 * - Conversion to valid numeric value happens SAFELY and INTENTIONALLY
 * - Uses useController (NOT register with valueAsNumber)
 * - displayValue is the ONLY source of truth for the <input> value
 * - field.onChange is called with a safe parsed number (never raw input strings)
 *
 * Key differences from MoneyInput:
 * - No currency prefix/symbol (m² display only)
 * - Integer mode by default (decimalPlaces: 0)
 * - Space as thousand separator
 */
export function AreaInput<TFieldValues extends FieldValues = FieldValues>({
  name,
  label,
  icon: Icon,
  placeholder = "0 m²",
  disabled,
  required,
  min = 0,
  className,
  containerClassName,
  error,
  control,
  defaultValue = "",
  onEnter,
}: AreaInputProps<TFieldValues>) {
  // ── Controller for RHF (like MoneyInput/EntidadLookupField) ─────────────────
  const {
    field,
    fieldState: { error: rhfError },
  } = useController({
    name,
    control,
    rules: {
      min: min as number,
    },
    defaultValue: defaultValue as never,
  });

  // ── Display state (STRING — the only thing the <input> sees) ──────────────
  const [displayValue, setDisplayValue] = useState<string>("");

  // ── Ref for cursor restoration ──────────────────────────────────────────────
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Sync flag: prevents circular RHF ↔ displayValue updates ───────────────
  // When true, the sync effect skips updating displayValue to avoid loops
  const isInternalUpdate = useRef(false);

  // ── Format a number with space-separated thousands and m² suffix ───────────
  const formatDisplay = useCallback(
    (val: number | "" | null | undefined): string => {
      if (val === "" || val === null || val === undefined) return "0 m²";
      const num = Number(val);
      if (isNaN(num) || !isFinite(num)) return "0 m²";

      const intPart = Math.round(num).toString();

      // Space as thousand separator (e.g. 1 000 000)
      const formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, " ");

      return `${formattedInt} m²`;
    },
    [],
  );

  // ── Sync displayValue from RHF field value (external changes: reset, defaultValues) ──
  useEffect(() => {
    if (isInternalUpdate.current) {
      isInternalUpdate.current = false;
      return;
    }
    const raw = field.value;
    // Only sync if field has a valid number
    if (raw === "" || raw === null || raw === undefined) {
      setDisplayValue(formatDisplay(0));
    } else {
      setDisplayValue(formatDisplay(raw));
    }
  }, [field.value, formatDisplay]);

  // ── Handle user typing ─────────────────────────────────────────────────────
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const input = e.target;
      const raw = input.value;
      const prevCursor = input.selectionStart ?? raw.length;
      const distFromEnd = raw.length - prevCursor;

      // Strip "m²", spaces, commas → raw numeric string
      const stripped = raw
        .replace(/m²/gi, "")
        .replace(/\s/g, "")
        .replace(/,/g, ".")
        .replace(/[^\d.]/g, "");

      // Empty → keep the numeric contract stable for schemas and cotización.
      if (stripped === "") {
        isInternalUpdate.current = true;
        setDisplayValue(formatDisplay(0));
        field.onChange(0 as never);
        return;
      }

      const parsed = parseFloat(stripped);
      if (isNaN(parsed) || !isFinite(parsed)) {
        return;
      }

      // Clamp to min and round to integer (area is always whole m²)
      const clamped = Math.max(Number(min) || 0, Math.round(parsed));

      // Update display with formatting
      const formatted = formatDisplay(clamped);
      isInternalUpdate.current = true;
      setDisplayValue(formatted);

      // Restore cursor: maintain same distance from end
      const newCursor = Math.max(0, formatted.length - distFromEnd);
      requestAnimationFrame(() => {
        if (inputRef.current) {
          inputRef.current.setSelectionRange(newCursor, newCursor);
        }
      });

      // Call field.onChange with the NUMBER — safe conversion happens HERE
      field.onChange(clamped as never);
    },
    [field, formatDisplay, min],
  );

  // ── Handle blur (re-format on leave) ──────────────────────────────────────
  const handleBlur = useCallback(
    (e: React.FocusEvent<HTMLInputElement>) => {
      const stripped = e.target.value
        .replace(/m²/gi, "")
        .replace(/\s/g, "")
        .replace(/[^\d.-]/g, "");

      if (stripped === "" || stripped === "-") {
        isInternalUpdate.current = true;
        setDisplayValue(formatDisplay(0));
        field.onChange(0 as never);
      } else {
        const parsed = parseFloat(stripped);
        if (!isNaN(parsed)) {
          const clamped = Math.max(Number(min) || 0, Math.round(parsed));
          isInternalUpdate.current = true;
          setDisplayValue(formatDisplay(clamped));
          // Also update field on blur with the clamped value
          field.onChange(clamped as never);
        }
      }
      field.onBlur();
    },
    [field, formatDisplay, min],
  );

  const hasIcon = !!Icon;

  const inputElement = (
    <input
      ref={inputRef}
      id={name}
      type="text"
      inputMode="decimal"
      placeholder={placeholder}
      disabled={disabled}
      aria-invalid={!!error || !!rhfError}
      className={cn(
        "h-10 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm",
        "ring-offset-background placeholder:text-muted-foreground",
        "focus-visible:outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "transition-colors duration-200",
        hasIcon ? "pl-10" : "",
        error
          ? "border-destructive focus-visible:border-destructive focus-visible:ring-destructive/20"
          : "",
        className ?? "",
      )}
      value={displayValue}
      onChange={handleChange}
      onBlur={handleBlur}
      onKeyDown={(e) => {
        if (e.key === "Enter" && onEnter) {
          e.preventDefault();
          onEnter();
        }
      }}
      name={name}
      autoComplete="off"
    />
  );

  return (
    <div className={cn("space-y-1.5", containerClassName ?? "")}>
      {label && (
        <Label
          htmlFor={name}
          className={cn(
            "text-sm font-medium",
            error ? "text-destructive" : "text-foreground",
          )}
        >
          {label}
          {required && <span className="text-destructive ml-0.5">*</span>}
        </Label>
      )}
      {hasIcon ? (
        <div className="relative">
          <div
            className={cn(
              "absolute left-3 top-1/2 -translate-y-1/2 transition-colors duration-200 pointer-events-none z-10",
              error ? "text-destructive" : "text-primary",
            )}
          >
            {Icon && <Icon className="h-4 w-4" />}
          </div>
          {inputElement}
        </div>
      ) : (
        inputElement
      )}
      {error && (
        <p className="text-xs text-destructive font-medium">{error.message}</p>
      )}
    </div>
  );
}
