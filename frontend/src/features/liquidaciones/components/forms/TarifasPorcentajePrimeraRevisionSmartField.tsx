"use client";

/**
 * TarifasPorcentajePrimeraRevisionSmartField — wraps TarifasPorcentajeSmartField
 * with auto-select-all behavior on first mount. Used by all PorcentajeObra types
 * (Edificaciones, Taludes, Impacto Vial).
 */
import { useEffect } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { TarifasPorcentajeSmartField } from "./TarifasPorcentajeSmartField";

interface TarifaVigente {
  id: string;
  especialidad: string;
  porcentaje_liquidacion: number;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface TarifasPorcentajePrimeraRevisionSmartFieldProps {
  methods: UseFormReturn<any>;
}

export function TarifasPorcentajePrimeraRevisionSmartField({
  methods,
}: TarifasPorcentajePrimeraRevisionSmartFieldProps) {
  // Fetch tariffs once to get all IDs for auto-selection
  const { data: tarifas } = useQuery<TarifaVigente[]>({
    queryKey: ["liquidaciones", "edificaciones", "tarifas-vigentes-auto"],
    queryFn: async () => {
      const { data } = await api.get("/liquidaciones/edificaciones/tarifas/vigentes");
      return data.data?.tarifas || [];
    },
  });

  // Auto-select all on first load
  useEffect(() => {
    if (tarifas && tarifas.length > 0) {
      const current = methods.getValues("tarifas_ids") as string[] | undefined;
      if (!current || current.length === 0) {
        const allIds = tarifas.map((t) => t.id);
        methods.setValue("tarifas_ids", allIds, { shouldValidate: true });
      }
    }
  }, [tarifas, methods]);

  return <TarifasPorcentajeSmartField methods={methods} />;
}
