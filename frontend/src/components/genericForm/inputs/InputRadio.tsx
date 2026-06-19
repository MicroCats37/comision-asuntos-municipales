// genericForm/inputs/InputRadio.tsx
"use client";

import type React from "react";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { InputComponentProps } from "./types";

/**
 * Grupo de radio buttons.
 */
export const InputRadio: React.FC<InputComponentProps> = ({
  field,
  register,
  id,
}) => {
  if (!field.options) {
    console.warn(`InputRadio: No options provided for field "${field.name}"`);
    return null;
  }

  // Nota: RadioGroup de shadcn/radix funciona mejor con Controller,
  // pero para mantener compatibilidad con la implementación original del usuario que usa register:
  // Se asume que el register maneja el onChange.
  // Si da problemas con Shadcn, se debería usar Controller, pero el usuario pidió no tocarlo.

  return (
    <RadioGroup
      disabled={field.disabled}
      className={field.className}
      {...register(field.name)}
    >
      {field.options.map((option) => (
        <div
          key={option.value?.toString() ?? `null-${option.label}`}
          className="flex items-center space-x-2"
        >
          <RadioGroupItem
            value={option.value?.toString() ?? ""}
            id={`${id}-${option.value ?? `null-${option.label}`}`}
          />
          <Label
            htmlFor={`${id}-${option.value ?? `null-${option.label}`}`}
            className="font-normal cursor-pointer"
          >
            {option.label}
          </Label>
        </div>
      ))}
    </RadioGroup>
  );
};
