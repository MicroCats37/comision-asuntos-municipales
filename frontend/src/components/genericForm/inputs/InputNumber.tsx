// genericForm/inputs/InputNumber.tsx
"use client";

import type React from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { InputComponentProps } from "./types";

/**
 * Input numérico.
 * Usa valueAsNumber de react-hook-form para conversión automática.
 * Soporta min/step para restricciones nativas del navegador.
 */
export const InputNumber: React.FC<InputComponentProps> = ({
  field,
  register,
  error,
  id,
}) => {
  const hasIcon = !!field.icon;
  const Icon = field.icon;

  const inputElement = (
    <Input
      id={id}
      type="number"
      placeholder={field.placeholder}
      disabled={field.disabled}
      min={field.min}
      step={field.step}
      aria-invalid={!!error}
      className={`${hasIcon ? "pl-10" : ""} ${field.className || ""}`}
      onKeyDown={field.onKeyDown}
      {...register(field.name, { valueAsNumber: true })}
    />
  );

  if (!hasIcon) return inputElement;

  return (
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
  );
};
