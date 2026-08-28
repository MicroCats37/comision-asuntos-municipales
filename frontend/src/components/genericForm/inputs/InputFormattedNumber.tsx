// InputFormattedNumber.tsx
"use client";

import type { KeyboardEvent } from "react";
/**
 * InputFormattedNumber — InputComponent-compatible wrapper for FormattedNumberInput.
 *
 * Implements the InputComponentProps interface so it can be registered in the
 * genericForm registry and used via GenericInput with field config.
 * Delegates to FormattedNumberInput for the actual smart-number behavior.
 *
 * Bridges field.onKeyDown → FormattedNumberInput.onEnter so GenericInput's
 * onKeyDown convention works for Enter-triggered cotizacion.
 */
import type { FieldPath, FieldValues } from "react-hook-form";
import { FormattedNumberInput } from "./FormattedNumberInput";
import type { InputComponentProps } from "./types";

export function InputFormattedNumber<
  TFieldValues extends FieldValues = FieldValues,
>({ field, control, error, id: _id }: InputComponentProps<TFieldValues>) {
  // Bridge field.onKeyDown (Enter handler) → onEnter prop.
  // FormattedNumberInput guards on Enter before calling onEnter and calls preventDefault.
  // We wrap field.onKeyDown to satisfy the () => void contract.
  const handler = field.onKeyDown;
  const onEnter = handler
    ? () => {
        // Create a synthetic KeyboardEvent to satisfy handler's signature.
        // FormattedNumberInput already called preventDefault on the real event.
        const synthetic = new KeyboardEvent("keydown", { key: "Enter" });
        handler(synthetic as unknown as React.KeyboardEvent<HTMLInputElement>);
      }
    : undefined;

  return (
    <FormattedNumberInput
      name={field.name as FieldPath<TFieldValues>}
      label={field.label}
      icon={field.icon}
      placeholder={field.placeholder}
      disabled={field.disabled}
      required={field.required}
      min={field.min}
      decimalPlaces={field.step ? 0 : 2}
      className={field.className}
      containerClassName={field.containerClassName}
      error={error}
      control={control}
      defaultValue={field.defaultValue as number | ""}
      onEnter={onEnter}
    />
  );
}
