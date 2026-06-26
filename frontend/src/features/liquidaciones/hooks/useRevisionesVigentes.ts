/**
 * Hook para obtener revisiones vigentes (especialidades/tarifas).
 * Usa useApiQuery genérico del proyecto.
 */
import { useApiQuery } from "@/hooks";
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import type { RevisionVigente } from "../types/revisiones-vigentes";

/** Data payload schema for revisiones vigentes */
const revisionVigentePayloadSchema = z.object({
  id: z.string(),
  especialidades: z.array(z.object({
    id: z.string(),
    nombre: z.string(),
  })),
  tarifa_id: z.string(),
  porcentaje_liquidacion: z.number(),
  derecho_minimo: z.number(),
  derecho_maximo: z.number().nullable(),
  porcentaje_minimo_uit: z.number(),
  habilitada: z.boolean(),
});

/** Wrapper schema for revisiones vigentes API response */
const revisionesVigentesResponseSchema = apiResponseSchema(
  z.object({
    revisiones: z.array(revisionVigentePayloadSchema),
  }),
);

export function useRevisionesVigentes() {
  const query = useApiQuery<
    z.infer<typeof revisionesVigentesResponseSchema>,
    RevisionVigente[]
  >({
    queryKey: ["liquidaciones", "revisiones-vigentes"],
    url: "/liquidaciones/edificaciones/revisiones-vigentes",
    schema: revisionesVigentesResponseSchema,
    queryOptions: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) {
          return [] as RevisionVigente[];
        }
        return data.data.revisiones;
      },
    },
  });

  return query;
}
