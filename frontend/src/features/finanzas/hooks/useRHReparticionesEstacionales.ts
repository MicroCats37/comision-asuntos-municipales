/**
 * Hook para listar Reparticiones Estacionales con su distribución completa.
 * Endpoints:
 *   GET  /finanzas/reparticiones-estacionales
 */
import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import { RHReparticionEstacionalSchema } from "../schemas/rh-reparticion-estacional.schema";

// ── List ────────────────────────────────────────────────────────────────────────

/** List returns a plain array wrapped in ApiResponse */
const listResponseSchema = apiResponseSchema(
  z.array(RHReparticionEstacionalSchema),
);
type ListResponseType = z.infer<typeof listResponseSchema>;

interface UseRHReparticionesEstacionalesProps {
  especialidadRevisionId?: string | null;
  periodo?: number | null;
  enabled?: boolean;
}

export function useRHReparticionesEstacionales({
  especialidadRevisionId,
  periodo,
  enabled = true,
}: UseRHReparticionesEstacionalesProps = {}) {
  const params: Record<string, string | number> = {};
  if (especialidadRevisionId)
    params.especialidad_revision_id = especialidadRevisionId;
  if (periodo) params.periodo = periodo;

  const query = useApiQuery<
    ListResponseType,
    z.infer<typeof RHReparticionEstacionalSchema>[]
  >({
    queryKey: [
      "finanzas",
      "reparticiones-estacionales",
      "list",
      especialidadRevisionId ?? "",
      periodo ?? "",
    ],
    url: "/finanzas/reparticiones-estacionales",
    schema: listResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      enabled,
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) {
          return [] as z.infer<typeof RHReparticionEstacionalSchema>[];
        }
        return data.data;
      },
    },
  });

  return {
    ...query,
    items: query.data ?? [],
  };
}
