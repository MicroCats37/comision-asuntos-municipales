// IncrementerInput.tsx
"use client";

import { Minus, Plus } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Control, FieldPath, FieldValues } from "react-hook-form";
import { useController } from "react-hook-form";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface IncrementerInputProps<
  TFieldValues extends FieldValues = FieldValues,
> {
  /** Field name */
  name: FieldPath<TFieldValues>;
  /** Display label */
  label?: string;
  /** Minimum value (default 1) */
  min?: number;
  /** Maximum value */
  max?: number;
  /** Suffix label shown next to the input (e.g. "visitas", "m²") */
  suffix?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Disabled state */
  disabled?: boolean;
  /** Required field */
  required?: boolean;
  /** RHF error message */
  error?: { message?: string };
  /** RHF control */
  control: Control<TFieldValues>;
  /** Default value */
  defaultValue?: number;
  /** Additional CSS classes for the input wrapper */
  containerClassName?: string;
}

const toNumber = (value: unknown): number => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

/**
 * IncrementerInput — numeric stepper input ( − N + ) with optional suffix.
 *
 * Pattern (matches MoneyInput / AreaInput discipline):
 * - UI manages a STRING representation (displayValue)
 * - field.onChange is called with a safe parsed number
 * - Uses useController (NOT register with valueAsNumber)
 * - Clamping to [min, max] applied at every entry point (typing, decrement, increment)
 *
 * Visual style matches the inline stepper used in TarifasVisitasNuevaRevisionSmartField:
 * - h-9 buttons flanking h-9 w-20 input
 * - tabular-nums, focus:border-primary + focus:ring-1 focus:ring-primary/30
 */
export function IncrementerInput<
  TFieldValues extends FieldValues = FieldValues,
>({
  name,
  label,
  min = 1,
  max,
  suffix,
  placeholder,
  disabled,
  required,
  error,
  control,
  defaultValue,
  containerClassName,
}: IncrementerInputProps<TFieldValues>) {
  const {
    field,
    fieldState: { error: rhfError },
  } = useController({
    name,
    control,
    defaultValue: defaultValue as never,
  });

  const [displayValue, setDisplayValue] = useState<string>(() =>
    field.value !== undefined && field.value !== null
      ? String(toNumber(field.value))
      : "",
  );

  const inputRef = useRef<HTMLInputElement>(null);
  const isInternalUpdate = useRef(false);

  const clamp = useCallback(
    (n: number): number => {
      const lo = Number(min);
      const hi = max !== undefined ? Number(max) : Infinity;
      return Math.max(lo, Math.min(hi, n));
    },
    [min, max],
  );

  const formatDisplay = useCallback((val: number): string => {
    if (!Number.isFinite(val)) return "";
    return String(Math.round(val));
  }, []);

  // ── Sync displayValue from RHF field value ─────────────────────────────────
  useEffect(() => {
    if (isInternalUpdate.current) {
      isInternalUpdate.current = false;
      return;
    }
    const raw = field.value;
    if (raw === "" || raw === null || raw === undefined) {
      setDisplayValue("");
    } else {
      setDisplayValue(formatDisplay(toNumber(raw)));
    }
  }, [field.value, formatDisplay]);

  const commit = useCallback(
    (n: number) => {
      const clamped = clamp(n);
      isInternalUpdate.current = true;
      setDisplayValue(formatDisplay(clamped));
      field.onChange(clamped as never);
    },
    [clamp, field, formatDisplay],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value;
      const stripped = raw.replace(/[^\d]/g, "");
      if (stripped === "") {
        commit(min);
        return;
      }
      const parsed = parseInt(stripped, 10);
      if (Number.isNaN(parsed)) return;
      commit(parsed);
    },
    [commit, min],
  );

  const handleBlur = useCallback(() => {
    field.onBlur();
  }, [field]);

  const handleDecrement = useCallback(() => {
    commit(toNumber(field.value) - 1);
  }, [commit, field.value]);

  const handleIncrement = useCallback(() => {
    commit(toNumber(field.value) + 1);
  }, [commit, field.value]);

  const hasError = !!error || !!rhfError;

  return (
    <div className={cn("space-y-2", containerClassName)}>
      {label && (
        <Label
          htmlFor={name}
          className={cn(
            "text-sm font-medium",
            hasError ? "text-destructive" : "leading-none",
          )}
        >
          {label}
          {required && <span className="text-destructive ml-0.5">*</span>}
        </Label>
      )}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleDecrement}
          disabled={disabled || toNumber(field.value) <= min}
          aria-label={`Disminuir ${label ?? name}`}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-background hover:border-primary/40 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Minus className="h-4 w-4" />
        </button>
        <input
          ref={inputRef}
          id={name}
          type="text"
          inputMode="numeric"
          value={displayValue}
          onChange={handleChange}
          onBlur={handleBlur}
          placeholder={placeholder}
          disabled={disabled}
          aria-invalid={hasError}
          className={cn(
            "h-9 w-20 rounded-lg border border-border bg-background px-3 text-center text-sm font-semibold tabular-nums",
            "focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30",
            "disabled:cursor-not-allowed disabled:opacity-50",
            hasError
              ? "border-destructive focus:border-destructive focus:ring-destructive/30"
              : "",
          )}
        />
        <button
          type="button"
          onClick={handleIncrement}
          disabled={
            disabled || (max !== undefined && toNumber(field.value) >= max)
          }
          aria-label={`Aumentar ${label ?? name}`}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-background hover:border-primary/40 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
        </button>
        {suffix && (
          <span className="text-xs text-muted-foreground">{suffix}</span>
        )}
      </div>
      {rhfError && (
        <p className="text-xs text-destructive font-medium">
          {rhfError.message}
        </p>
      )}
    </div>
  );
}
