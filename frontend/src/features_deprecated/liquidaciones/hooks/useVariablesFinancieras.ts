/**
 * Hook para obtener variables financieras vigentes (IGV/UIT).
 * Usa useApiQuery genérico del proyecto.
 */

import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { VariablesFinancieras } from "../types/liquidacion-edificaciones";

/** Data payload schema — only the inner data shape */
const variablesFinancierasPayloadSchema = z.object({
  igv_valor: z.number(),
  igv_periodo_inicio: z.string(),
  uit_valor: z.number(),
  uit_periodo_inicio: z.string(),
});

/** Full envelope schema using shared helper */
const finanzasVariablesResponseSchema = apiResponseSchema(
  variablesFinancierasPayloadSchema,
);

/** Fallback values when API fails or returns null data */
const DEFAULT_VARIABLES: VariablesFinancieras = {
  igv_valor: 0.18,
  igv_periodo_inicio: "",
  uit_valor: 5150,
  uit_periodo_inicio: "",
};

export function useVariablesFinancieras() {
  const query = useApiQuery<
    z.infer<typeof finanzasVariablesResponseSchema>,
    VariablesFinancieras
  >({
    queryKey: ["finanzas", "variables", "vigentes"],
    url: "/finanzas/variables/vigentes",
    schema: finanzasVariablesResponseSchema,
    queryOptions: {
      staleTime: 1000 * 60 * 5, // 5 minutes - variables financieras no cambian frecuentemente
      select: (envelope) => {
        // Only return data if success is true and data exists
        if (envelope.success && envelope.data) {
          return envelope.data;
        }
        return DEFAULT_VARIABLES;
      },
    },
  });

  return query;
}
