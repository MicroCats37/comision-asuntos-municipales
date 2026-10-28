// MoneyInput.tsx
"use client";

import type { LucideIcon } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Control, FieldPath, FieldValues } from "react-hook-form";
import { useController } from "react-hook-form";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

function normalizeMoneyText(raw: string): string {
  const cleaned = raw
    .replace(/S\/\s*/g, "")
    .replace(/\s/g, "")
    .replace(/,/g, ".")
    .replace(/[^\d.-]/g, "");
  const isNegative = cleaned.startsWith("-");
  const unsigned = cleaned.replace(/-/g, "");
  if (unsigned === "") return isNegative ? "-" : "";

  const hasDecimalSeparator = unsigned.includes(".");
  const [rawIntegerPart = "", ...decimalParts] = unsigned.split(".");
  const integerPart = rawIntegerPart.replace(/^0+(?=\d)/, "");
  const decimals = decimalParts.join("").slice(0, 2);
  return `${isNegative ? "-" : ""}${integerPart || "0"}${
    hasDecimalSeparator ? `.${decimals}` : ""
  }`;
}

function parseMoneyText(value: string): number | undefined {
  if (value === "" || value === "-" || value === "." || value === "-.") {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

interface MoneyInputProps<TFieldValues extends FieldValues = FieldValues> {
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
 * SmartMoneyInput — true smart amount component.
 *
 * Pattern (matches EntidadLookupField discipline):
 * - UI manages a STRING representation (displayValue)
 * - Internal logic handles formatting/parsing/conditions
 * - Conversion to valid numeric value happens SAFELY and INTENTIONALLY
 * - No fighting with RHF valueAsNumber — use useController + field.onChange
 *
 * Key differences from the wrong approach:
 * - Uses useController (NOT register with valueAsNumber)
 * - displayValue is the ONLY source of truth for the <input> value
 * - field.onChange is called with a safe parsed number (never raw input strings)
 * - No RHF conflicts — the component controls exactly what value gets sent
 */
export function MoneyInput<TFieldValues extends FieldValues = FieldValues>({
  name,
  label,
  icon: Icon,
  placeholder = "S/ 0.00",
  disabled,
  required,
  className,
  containerClassName,
  error,
  control,
  defaultValue = "",
  onEnter,
}: MoneyInputProps<TFieldValues>) {
  // ── Controller for RHF (like EntidadLookupField) ─────────────────────────
  const {
    field,
    fieldState: { error: rhfError },
  } = useController({
    name,
    control,
    defaultValue: defaultValue as never,
  });

  // ── Display state (STRING — the only thing the <input> sees) ──────────────
  const [displayValue, setDisplayValue] = useState<string>("");

  // ── Ref for cursor restoration ──────────────────────────────────────────────
  const inputRef = useRef<HTMLInputElement>(null);
  const isFocusedRef = useRef(false);

  // ── Format a number with S/ prefix and space-separated thousands ───────────
  const formatDisplay = useCallback(
    (val: number | "" | null | undefined): string => {
      if (val === "" || val === null || val === undefined) return "";
      const num = Number(val);
      if (!Number.isFinite(num)) return "";

      const fixed = num.toFixed(2);
      const [intPart, decPart] = fixed.split(".");

      // Space as thousand separator (e.g. 1 000 000)
      const formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, " ");

      // Only show decimal part when non-zero
      if (decPart === "00") return `S/ ${formattedInt}`;
      if (decPart[1] === "0") return `S/ ${formattedInt}.${decPart[0]}`;
      return `S/ ${formattedInt}.${decPart}`;
    },
    [],
  );

  // ── Sync displayValue from RHF field value (external changes: reset, defaultValues) ──
  useEffect(() => {
    if (isFocusedRef.current) return;
    const raw = field.value;
    setDisplayValue(formatDisplay(raw));
  }, [field.value, formatDisplay]);

  // ── Handle user typing ─────────────────────────────────────────────────────
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const input = e.target;
      const raw = input.value;
      const prevCursor = input.selectionStart ?? raw.length;
      const stripped = normalizeMoneyText(raw);
      const formatted = stripped === "" ? "" : `S/ ${stripped}`;
      setDisplayValue(formatted);

      const normalizedBeforeCursor = normalizeMoneyText(
        raw.slice(0, prevCursor),
      );
      const newCursor =
        normalizedBeforeCursor === "" ? 0 : 3 + normalizedBeforeCursor.length;
      requestAnimationFrame(() => {
        if (inputRef.current) {
          inputRef.current.setSelectionRange(newCursor, newCursor);
        }
      });

      field.onChange(parseMoneyText(stripped) as never);
    },
    [field],
  );

  // ── Handle blur (re-format on leave) ──────────────────────────────────────
  const handleBlur = useCallback(
    (e: React.FocusEvent<HTMLInputElement>) => {
      const stripped = normalizeMoneyText(e.target.value);
      const parsed = parseMoneyText(stripped);
      isFocusedRef.current = false;
      setDisplayValue(formatDisplay(parsed));
      field.onChange(parsed as never);
      field.onBlur();
    },
    [field, formatDisplay],
  );

  const hasIcon = !!Icon;
  const visibleError = error ?? rhfError;

  const inputElement = (
    <input
      ref={inputRef}
      id={name}
      type="text"
      inputMode="decimal"
      placeholder={placeholder}
      disabled={disabled}
      aria-invalid={!!visibleError}
      aria-describedby={visibleError ? `${name}-error` : undefined}
      className={cn(
        "h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm",
        "ring-offset-background placeholder:text-muted-foreground",
        "focus-visible:outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "transition-colors duration-200",
        hasIcon ? "pl-10" : "",
        visibleError
          ? "border-destructive focus-visible:border-destructive focus-visible:ring-destructive/20"
          : "",
        className ?? "",
      )}
      value={displayValue}
      onFocus={() => {
        isFocusedRef.current = true;
      }}
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
    <div className={cn("space-y-2", containerClassName ?? "")}>
      {label && (
        <Label
          htmlFor={name}
          className={cn(
            "text-sm font-medium ",
            visibleError ? "text-destructive" : "leading-none",
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
              visibleError ? "text-destructive" : "text-primary",
            )}
          >
            {Icon && <Icon className="h-4 w-4" />}
          </div>
          {inputElement}
        </div>
      ) : (
        inputElement
      )}
      {visibleError?.message && (
        <p
          id={`${name}-error`}
          className="text-xs text-destructive font-medium"
          role="alert"
        >
          {visibleError.message}
        </p>
      )}
    </div>
  );
}
