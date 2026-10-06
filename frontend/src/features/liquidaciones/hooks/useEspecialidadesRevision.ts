/**
 * Hook para obtener el catálogo de Especialidades de Revision.
 * Endpoint: GET /liquidaciones/especialidades-revision
 *
 * Sin filtros, sin paginación. Catalog — staleTime alto.
 */
import type { z } from "zod";
import { useApiQuery } from "@/hooks";
import {
  EspecialidadesRevisionResponseSchema,
  type EspecialidadRevisionOption,
} from "../schemas/especialidades-revision.schema";

export function useEspecialidadesRevision() {
  const query = useApiQuery<
    z.infer<typeof EspecialidadesRevisionResponseSchema>,
    EspecialidadRevisionOption[]
  >({
    queryKey: ["liquidaciones", "especialidades-revision"],
    url: "/liquidaciones/especialidades-revision",
    schema: EspecialidadesRevisionResponseSchema,
    params: undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 10, // 10 minutes — catalog changes rarely
      select: (data) => {
        if (!data.data) {
          return [] as EspecialidadRevisionOption[];
        }
        return data.data.especialidades;
      },
    },
  });

  return query;
}
