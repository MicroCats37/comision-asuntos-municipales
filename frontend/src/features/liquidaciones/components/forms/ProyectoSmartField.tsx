"use client";

import { Building2, FileText, MapPin, User } from "lucide-react";
/**
 * ProyectoSmartField — Smart Field for proyecto section.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<EdificacionesFormData>` from parent
 * - Renders: denominacion, nombre_propietario, direccion, distrito_id (select/searchable),
 *   entidad (tipo_documento, numero_documento, razon_social)
 * - Uses GenericInput internally
 */
import type { UseFormReturn } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import type { EdificacionesFormData } from "../../schemas/liquidacion-edificaciones-form.schema";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface ProyectoSmartFieldProps {
  methods: UseFormReturn<any>;
}

export function ProyectoSmartField({ methods }: ProyectoSmartFieldProps) {
  const {
    register,
    control,
    formState: { errors },
  } = methods;

  return (
    <div className="space-y-4 rounded-xl border border-border/50 bg-card p-4">
      <div className="flex items-center gap-2 border-b border-border/40 pb-2 text-primary">
        <FileText className="h-4 w-4" />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
          Datos del Proyecto
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Denominación */}
        <GenericInput
          field={{
            name: "denominacion",
            label: "Denominación",
            type: "text",
            placeholder: "Nombre del proyecto",
            icon: FileText,
            required: true,
          }}
          register={register as never}
          control={control as never}
          errors={errors}
        />

        {/* Nombre del Propietario */}
        <GenericInput
          field={{
            name: "nombre_propietario",
            label: "Nombre del Propietario",
            type: "text",
            placeholder: "Nombre del propietario o representante legal",
            icon: User,
            required: true,
          }}
          register={register as never}
          control={control as never}
          errors={errors}
        />

        {/* Dirección */}
        <GenericInput
          field={{
            name: "direccion",
            label: "Dirección",
            type: "text",
            placeholder: "Dirección del proyecto",
            icon: MapPin,
            required: true,
            containerClassName: "md:col-span-2",
          }}
          register={register as never}
          control={control as never}
          errors={errors}
        />

        {/* Distrito ID */}
        <GenericInput
          field={{
            name: "distrito_id",
            label: "Distrito",
            type: "searchable-select",
            placeholder: "Seleccione distrito",
            icon: Building2,
            required: true,
            // Options would be populated via a query in a real implementation
            options: [],
          }}
          register={register as never}
          control={control as never}
          errors={errors}
        />
      </div>

      {/* Entidad Section */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          <Building2 className="h-3.5 w-3.5 text-primary/70" />
          <span>Datos de la Entidad</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Entidad Tipo Documento */}
          <GenericInput
            field={{
              name: "entidad_tipo_documento",
              label: "Tipo de Documento",
              type: "select",
              required: true,
              options: [
                { label: "RUC", value: "RUC" },
                { label: "DNI", value: "DNI" },
              ],
            }}
            register={register as never}
            control={control as never}
            errors={errors}
          />

          {/* Entidad Número Documento */}
          <GenericInput
            field={{
              name: "entidad_numero_documento",
              label: "Número de Documento",
              type: "text",
              placeholder: "Número de documento",
              required: true,
            }}
            register={register as never}
            control={control as never}
            errors={errors}
          />

          {/* Entidad Razón Social */}
          <GenericInput
            field={{
              name: "entidad_razon_social",
              label: "Razón Social",
              type: "text",
              placeholder: "Razón social o nombre completo",
              required: true,
              containerClassName: "md:col-span-2",
            }}
            register={register as never}
            control={control as never}
            errors={errors}
          />
        </div>
      </div>
    </div>
  );
}
