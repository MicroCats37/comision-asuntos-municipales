"use client";

import { CalendarDays, Hash } from "lucide-react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";

interface LegacyRegistroFieldsProps<T extends FieldValues> {
  methods: UseFormReturn<T>;
}

export function LegacyRegistroFields<T extends FieldValues>({
  methods,
}: LegacyRegistroFieldsProps<T>) {
  return (
    <section className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3">
      <div className="mb-2">
        <p className="text-sm font-bold text-foreground">Identidad histórica</p>
        <p className="text-xs text-muted-foreground">
          Estos datos identifican el documento original y determinan las
          tarifas aplicables.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <GenericInput
          field={{
            name: "numero",
            label: "Número histórico",
            type: "number",
            min: 1,
            step: 1,
            icon: Hash,
            required: true,
            placeholder: "Ej. 1250",
            containerClassName: "col-span-1",
          }}
          register={methods.register as never}
          control={methods.control as never}
          errors={methods.formState.errors}
        />
        <GenericInput
          field={{
            name: "fecha_registro",
            label: "Fecha de registro",
            type: "date",
            icon: CalendarDays,
            required: true,
            placeholder: "Seleccione la fecha histórica",
            containerClassName: "col-span-1",
          }}
          register={methods.register as never}
          control={methods.control as never}
          errors={methods.formState.errors}
        />
      </div>
    </section>
  );
}
