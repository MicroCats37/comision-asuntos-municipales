"use client";

/**
 * TarifasPorcentajePrimeraRevisionSmartField — wraps TarifasPorcentajeSmartField
 * with auto-select-all behavior on first mount. Used by all PorcentajeObra types
 * (Edificaciones, Taludes, Impacto Vial).
 *
 * NEW contract: the API returns a SINGLE tariff + especialidades_disponibles array.
 * Auto-selects ALL especialidades on mount.
 */
import { useEffect } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useTarifasVigentesPorcentaje } from "../../hooks/useTarifasVigentes";
import { TarifasPorcentajeSmartField } from "./TarifasPorcentajeSmartField";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface TarifasPorcentajePrimeraRevisionSmartFieldProps {
  methods: UseFormReturn<any>;
  /** Tipo de liquidación para el endpoint (default: edificaciones) */
  tipo?: string;
}

export function TarifasPorcentajePrimeraRevisionSmartField({
  methods,
  tipo = "edificaciones",
}: TarifasPorcentajePrimeraRevisionSmartFieldProps) {
  // Fetch tarifas + especialidades once for auto-select-all
  const { data } = useTarifasVigentesPorcentaje(tipo);

  // Auto-select ALL especialidades on first load
  useEffect(() => {
    if (
      data?.especialidades_disponibles &&
      data.especialidades_disponibles.length > 0
    ) {
      const current = methods.getValues("especialidades_seleccionadas") as
        | string[]
        | undefined;
      if (!current || current.length === 0) {
        const allIds = data.especialidades_disponibles.map((e) => e.id);
        methods.setValue("especialidades_seleccionadas", allIds, {
          shouldValidate: true,
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  return <TarifasPorcentajeSmartField methods={methods} tipo={tipo} />;
}
