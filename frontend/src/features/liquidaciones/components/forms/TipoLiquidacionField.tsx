"use client";

import { Building2 } from "lucide-react";
/**
 * TipoLiquidacionField — Searchable select para Tipo de Liquidación.
 *
 * Sigue el patrón de `MunicipalidadField` (LiquidacionFormBodyBase):
 * usa `GenericInput` con `type: "searchable-select"`, opciones derivadas del
 * hook `useTiposLiquidacion()` (GET /delegados/tipos-liquidacion).
 *
 * Response shape: `{ tipos: [{ id, codigo, nombre }] }` — no paginado.
 */
import type { Control, FieldErrors } from "react-hook-form";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { useTiposLiquidacion } from "../../hooks/useTiposLiquidacion";

interface TipoLiquidacionFieldProps {
  register: unknown;
  control: Control<any>;
  errors: FieldErrors<any>;
}

export function TipoLiquidacionField({
  register,
  control,
  errors,
}: TipoLiquidacionFieldProps) {
  const { data: tipos = [], isLoading } = useTiposLiquidacion();
  return (
    <GenericInput
      field={{
        name: "tipo_liquidacion_id",
        label: "Tipo de Liquidación",
        type: "searchable-select",
        containerClassName: "sm:col-span-1",
        placeholder: isLoading ? "Cargando..." : "Seleccione tipo de liquidación",
        icon: Building2,
        required: true,
        options: tipos.map((t) => ({
          label: `${t.codigo} · ${t.nombre}`,
          value: t.id,
        })),
        isLoading,
      }}
      register={register as never}
      control={control as never}
      errors={errors}
    />
  );
}