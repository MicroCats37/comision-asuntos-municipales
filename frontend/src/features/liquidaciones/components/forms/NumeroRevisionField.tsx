"use client";

import { RefreshCw } from "lucide-react";
import type { Control, FieldErrors, UseFormRegister } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { NUMERO_REVISION_OPTIONS } from "../../utils/numeroRevision";

interface NumeroRevisionFieldProps {
  // biome-ignore lint/suspicious/noExplicitAny: RHF generics pattern matches the existing form fields
  register: UseFormRegister<any>;
  // biome-ignore lint/suspicious/noExplicitAny: RHF generics pattern matches the existing form fields
  control: Control<any>;
  // biome-ignore lint/suspicious/noExplicitAny: RHF generics pattern matches the existing form fields
  errors: FieldErrors<any>;
  disabled?: boolean;
}

/**
 * NumeroRevisionField — campo reutilizable del número de revisión.
 *
 * El número de revisión es una ETIQUETA EDITABLE elegida por el usuario (no
 * una secuencia derivada), por eso se ofrece como selector con las únicas
 * opciones que el contrato backend admite: {1, 3, 5}.
 *
 * Se renderiza en la segunda celda del grid "Datos del Trámite", junto al
 * campo específico del motor (valor_declarado / area_solicitada).
 *
 * NO se usa en Inspección de Obra: ese tipo es revision-less y permanece
 * fijo en revisión 1.
 */
export function NumeroRevisionField({
  register,
  control,
  errors,
  disabled,
}: NumeroRevisionFieldProps) {
  return (
    <GenericInput
      field={{
        name: "numero_revision",
        label: "Número de Revisión",
        type: "select",
        valueType: "number",
        containerClassName: "sm:col-span-1",
        placeholder: "Seleccione la revisión",
        icon: RefreshCw,
        required: true,
        disabled,
        options: NUMERO_REVISION_OPTIONS,
        helperText: "Etiqueta editable de la revisión (1, 3 o 5).",
      }}
      register={register as never}
      control={control as never}
      errors={errors}
    />
  );
}
