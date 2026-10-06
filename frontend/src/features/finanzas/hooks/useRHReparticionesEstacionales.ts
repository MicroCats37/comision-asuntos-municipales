/**
 * Hooks para listar y obtener detalle de Reparticiones Estacionales.
 * Endpoints:
 *   GET  /finanzas/reparticiones-estacionales
 *   GET  /finanzas/reparticiones-estacionales/{id}
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import { useApiQuery } from "@/hooks";
import {
  RHReparticionEstacionalListItemSchema,
  RHReparticionEstacionalDetalleSchema,
  RHReparticionEstacionalCotizarResponseSchema,
  RHReparticionEstacionalDetalleResponseSchema,
} from "../schemas/rh-reparticion-estacional.schema";

// ── List ────────────────────────────────────────────────────────────────────────

/** List returns a plain array wrapped in ApiResponse */
const listResponseSchema = apiResponseSchema(
  z.array(RHReparticionEstacionalListItemSchema),
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
    z.infer<typeof RHReparticionEstacionalListItemSchema>[]
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
          return [] as z.infer<typeof RHReparticionEstacionalListItemSchema>[];
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

// ── Detail ─────────────────────────────────────────────────────────────────────

interface UseRHReparticionEstacionalDetalleProps {
  reparticionId: string | null;
  enabled?: boolean;
}

export function useRHReparticionEstacionalDetalle({
  reparticionId,
  enabled = true,
}: UseRHReparticionEstacionalDetalleProps) {
  const query = useApiQuery<
    z.infer<typeof RHReparticionEstacionalDetalleResponseSchema>,
    z.infer<typeof RHReparticionEstacionalDetalleSchema> | null
  >({
    queryKey: [
      "finanzas",
      "reparticiones-estacionales",
      "detalle",
      reparticionId ?? "",
    ],
    url: reparticionId
      ? `/finanzas/reparticiones-estacionales/${reparticionId}`
      : null,
    schema: RHReparticionEstacionalDetalleResponseSchema,
    queryOptions: {
      enabled: !!reparticionId && enabled,
      staleTime: 1000 * 60 * 2, // 2 minutes
      select: (data) => {
        if (!data.data) {
          return null as z.infer<
            typeof RHReparticionEstacionalDetalleSchema
          > | null;
        }
        return data.data;
      },
    },
  });

  return {
    ...query,
    detalle: query.data ?? null,
  };
}
