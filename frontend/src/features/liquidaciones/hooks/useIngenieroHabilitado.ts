/**
 * Hook para validar CIP de ingeniero habilitado.
 * GET /ingenieros/habilitados/{cip}
 */

import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { IngenieroHabilitado } from "../types/proyectista";

/** Data payload schema for ingeniero habilitado */
const ingenieroHabilitadoPayloadSchema = z.object({
  cip: z.string(),
  nombres: z.string(),
  apellidos: z.string(),
  habilitado: z.boolean(),
  capitulo: z.string().nullable(),
});

/** Full envelope schema */
const ingenieroHabilitadoResponseSchema = apiResponseSchema(
  ingenieroHabilitadoPayloadSchema,
);

export function useIngenieroHabilitado(cip: string | null) {
  const query = useApiQuery<
    z.infer<typeof ingenieroHabilitadoResponseSchema>,
    IngenieroHabilitado | null
  >({
    queryKey: ["ingenieros", "habilitados", cip],
    url: cip ? `/ingenieros/habilitados/${cip}` : null,
    schema: ingenieroHabilitadoResponseSchema,
    queryOptions: {
      enabled: !!cip && cip.length >= 3 && cip.length <= 6,
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) {
          return null;
        }
        return data.data;
      },
    },
  });

  return query;
}
