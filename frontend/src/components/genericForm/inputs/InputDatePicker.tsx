// genericForm/inputs/InputDatePicker.tsx
"use client";

import { format } from "date-fns";
import { es } from "date-fns/locale";
import { CalendarIcon } from "lucide-react";
import { Controller } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { InputComponentProps } from "./types";

/**
 * DatePicker usando shadcn Calendar.
 * Guarda la fecha como string ISO (YYYY-MM-DD).
 * Soporta icono opcional a la izquierda.
 */
export const InputDatePicker: React.FC<InputComponentProps> = ({
  field,
  control,
  error,
  id,
}) => {
  const hasIcon = !!field.icon;
  const Icon = field.icon || CalendarIcon;

  return (
    <Controller
      name={field.name}
      control={control}
      render={({ field: controllerField }) => {
        // Convertir string a Date si existe
        const selectedDate = controllerField.value
          ? new Date(controllerField.value)
          : undefined;

        return (
          <Popover>
            <PopoverTrigger asChild>
              <Button
                id={id}
                variant="outline"
                disabled={field.disabled}
                aria-invalid={!!error}
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !controllerField.value && "text-muted-foreground",
                  hasIcon && "pl-10",
                  field.className,
                )}
              >
                <div
                  className={cn(
                    "absolute left-3 top-1/2 -translate-y-1/2 transition-colors duration-200 pointer-events-none z-10",
                    error ? "text-destructive" : "text-primary",
                  )}
                >
                  <Icon className="h-4 w-4" />
                </div>
                {controllerField.value ? (
                  format(selectedDate!, "PPP", { locale: es })
                ) : (
                  <span>{field.placeholder || "Seleccionar fecha..."}</span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={selectedDate}
                onSelect={(date) => {
                  // Guardar como string ISO (solo fecha, sin hora)
                  controllerField.onChange(
                    date ? format(date, "yyyy-MM-dd") : null,
                  );
                }}
                locale={es}
                initialFocus
                captionLayout="dropdown"
                startMonth={new Date(new Date().getFullYear() - 100, 0)}
                endMonth={new Date()}
              />
            </PopoverContent>
          </Popover>
        );
      }}
    />
  );
};
