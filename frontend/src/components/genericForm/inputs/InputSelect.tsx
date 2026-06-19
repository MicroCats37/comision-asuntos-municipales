// genericForm/inputs/InputSelect.tsx
"use client";

import type React from "react";
import { Controller } from "react-hook-form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { InputComponentProps } from "./types";

/**
 * Select dropdown con opciones estáticas.
 * Soporta conversión de tipos (string/number/boolean) via valueType.
 * Soporta icono opcional a la izquierda.
 */
export const InputSelect: React.FC<InputComponentProps> = ({
  field,
  control,
  error,
  id,
}) => {
  if (!field.options) {
    console.warn(`InputSelect: No options provided for field "${field.name}"`);
    return null;
  }

  // TypeScript narrowing: after guard, options is guaranteed to exist
  const options = field.options;
  const hasIcon = !!field.icon;
  const Icon = field.icon;

  const selectElement = (
    <Controller
      name={field.name}
      control={control}
      render={({ field: controllerField }) => (
        <Select
          disabled={field.disabled || field.isLoading}
          value={controllerField.value?.toString() || ""}
          onValueChange={(value) => {
            let convertedValue: unknown = value;

            // Conversión de tipos
            if (field.valueType === "number") {
              convertedValue = Number(value);
            } else if (field.valueType === "boolean") {
              convertedValue = value === "true";
            } else if (!field.valueType && options.length > 0) {
              // Inferir tipo de la primera opción (ignorar nulos)
              const firstVal = options.find((o) => o.value !== null)?.value;
              if (typeof firstVal === "number") {
                convertedValue = Number(value);
              }
            }

            controllerField.onChange(convertedValue);
          }}
        >
          <SelectTrigger
            id={id}
            aria-invalid={!!error}
            className={`${hasIcon ? "pl-10" : ""} ${field.className || ""}`}
          >
            <SelectValue placeholder={field.placeholder || "Seleccione..."} />
          </SelectTrigger>
          <SelectContent>
            {field.isLoading ? (
              <div className="p-2 text-center text-sm text-muted-foreground">
                Cargando...
              </div>
            ) : options.length === 0 ? (
              <div className="p-2 text-center text-sm text-muted-foreground">
                No hay opciones
              </div>
            ) : (
              options.map((option) => (
                <SelectItem
                  key={option.value?.toString() ?? `null-${option.label}`}
                  value={option.value?.toString() ?? ""}
                >
                  {option.label}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
      )}
    />
  );

  if (!hasIcon) return selectElement;

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
      {selectElement}
    </div>
  );
};
