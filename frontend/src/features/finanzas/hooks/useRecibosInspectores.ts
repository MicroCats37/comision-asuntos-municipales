/**
 * Hook para listar Recibos de Honorarios de Inspectores con paginación.
 * Endpoint: GET /finanzas/recibos-inspectores
 * Filtros: inspector_id
 * Nota: El endpoint ahora retorna ReciboHonorarioInspectorMensual (agrupado por periodo+inspector),
 * no ReciboHonorarioInspector (individual por LiquidacionInspector).
 */

import { paginatedResponseSchema } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { ReciboHonorarioInspectorMensual } from "../schemas/recibo-honorario.schema";
import { rhInspectorMensualListItemSchema } from "../schemas/recibo-honorario.schema";

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(rhInspectorMensualListItemSchema),
);

interface UseRecibosInspectoresProps {
  page?: number;
  pageSize?: number;
  inspectorId?: string;
  enabled?: boolean;
}

export function useRecibosInspectores({
  page = 1,
  pageSize = 10,
  inspectorId,
  enabled = true,
}: UseRecibosInspectoresProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (inspectorId) params.inspector_id = inspectorId;

  const query = useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-inspectores",
      "mensual",
      page,
      pageSize,
      inspectorId,
    ],
    url: "/finanzas/recibos-inspectores",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as ReciboHonorarioInspectorMensual[],
            total: 0,
            page,
            page_size: pageSize,
            total_pages: 1,
          };
        }
        return data.data;
      },
    },
  });

  return {
    ...query,
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
    totalPages: query.data?.total_pages ?? 1,
  };
}
