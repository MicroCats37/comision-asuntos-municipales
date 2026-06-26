/**
 * Hook para obtener delegados vigentes para una municipalidad y revisión.
 * Usa useApiQuery genérico del proyecto.
 */
import { useApiQuery } from "@/hooks";
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import type { DelegadoVigente } from "../types/liquidacion-edificaciones";

/** Data payload schema for delegado vigente */
const especialidadBasicaDelegadoSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const delegadoVigentePayloadSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
  especialidad: especialidadBasicaDelegadoSchema,
  tipo: z.string(),
});

/** Wrapper schema for delegados vigentes API response */
const delegadosVigentesResponseSchema = apiResponseSchema(
  z.object({
    delegados: z.array(delegadoVigentePayloadSchema),
  }),
);

export function useDelegadosVigentes(
  municipalidadId: string | null,
  revisionId: string | null,
  categoria: string = "Edificaciones"
) {
  const query = useApiQuery<
    z.infer<typeof delegadosVigentesResponseSchema>,
    DelegadoVigente[]
  >({
    queryKey: ["liquidaciones", "delegados-vigentes", municipalidadId, revisionId, categoria],
    url: "/liquidaciones/edificaciones/delegados/vigentes",
    params:
      municipalidadId && revisionId
        ? { municipalidad_id: municipalidadId, revision_id: revisionId, categoria }
        : undefined,
    schema: delegadosVigentesResponseSchema,
    queryOptions: {
      enabled: !!municipalidadId && !!revisionId,
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) {
          return [] as DelegadoVigente[];
        }
        return data.data.delegados;
      },
    },
  });

  return query;
}
