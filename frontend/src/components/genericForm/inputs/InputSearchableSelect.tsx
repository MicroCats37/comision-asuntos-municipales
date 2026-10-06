// genericForm/inputs/InputSearchableSelect.tsx
"use client";

import { List } from "lucide-react";
import type React from "react";
import { Controller } from "react-hook-form";
import { SearchableSelect } from "@/components/ui/searchable-select";
import type { InputComponentProps } from "./types";

/**
 * SearchableSelect dropdown con opciones estáticas y búsqueda.
 * Soporta conversión de tipos (string/number/boolean) via valueType.
 *
 * NO hardcodea colores — usa shadcn tokens y className del field.
 */
export const InputSearchableSelect: React.FC<InputComponentProps> = ({
  field,
  control,
  error,
  id,
  hideErrorMessage = false,
}) => {
  if (!field.options) {
    console.warn(
      `InputSearchableSelect: No options provided for field "${field.name}"`,
    );
    return null;
  }

  // Default icon: List
  const DefaultIcon = List;
  const Icon = field.icon || DefaultIcon;

  // Convert FormField.options (string | number | boolean | null) to SearchableSelectOption[] (string)
  const searchableOptions = field.options.map((option) => ({
    value:
      option.value === null
        ? "__none__"
        : typeof option.value === "boolean"
          ? option.value.toString()
          : String(option.value),
    label: option.label,
  }));

  return (
    <Controller
      name={field.name}
      control={control}
      render={({ field: cf }) => {
        // Convert cf.value back to string for SearchableSelect
        let stringValue: string | null = null;
        if (cf.value !== null && cf.value !== undefined) {
          if (typeof cf.value === "boolean") {
            stringValue = cf.value.toString();
          } else if (typeof cf.value === "number") {
            stringValue = cf.value.toString();
          } else {
            stringValue = cf.value as string;
          }
        }

        return (
          <SearchableSelect
            id={id}
            label={field.label}
            value={stringValue}
            onValueChange={(val) => {
              if (val === null || val === "__none__") {
                cf.onChange(null);
                return;
              }

              // Conversión de tipos según field.valueType
              let convertedValue: string | number | boolean = val;
              if (field.valueType === "number") {
                convertedValue = Number(val);
              } else if (field.valueType === "boolean") {
                convertedValue = val === "true";
              }
              // default: string (no conversion needed)

              cf.onChange(convertedValue);
            }}
            options={searchableOptions}
            placeholder={field.placeholder || "Buscar..."}
            icon={Icon}
            disabled={field.disabled || field.isLoading}
            error={!!error}
            errorMessage={error?.message}
            className={field.className}
            showLabel={false}
            hideErrorMessage={hideErrorMessage}
          />
        );
      }}
    />
  );
};
