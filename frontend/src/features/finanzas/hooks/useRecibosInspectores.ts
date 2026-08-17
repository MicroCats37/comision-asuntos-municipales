/**
 * Hook para listar Recibos de Honorarios de Inspectores con paginación.
 * Endpoint: GET /finanzas/recibos-inspectores
 * Filtros: inspector_id, liquidacion_id
 */

import { paginatedResponseSchema } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { ReciboHonorarioInspector } from "../schemas/recibo-honorario.schema";
import { reciboHonorarioInspectorSchema } from "../schemas/recibo-honorario.schema";

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(reciboHonorarioInspectorSchema),
);

interface UseRecibosInspectoresProps {
  page?: number;
  pageSize?: number;
  inspectorId?: string;
  liquidacionId?: string;
  enabled?: boolean;
}

export function useRecibosInspectores({
  page = 1,
  pageSize = 10,
  inspectorId,
  liquidacionId,
  enabled = true,
}: UseRecibosInspectoresProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (inspectorId) params.inspector_id = inspectorId;
  if (liquidacionId) params.liquidacion_id = liquidacionId;

  const query = useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-inspectores",
      page,
      pageSize,
      inspectorId,
      liquidacionId,
    ],
    url: "/finanzas/recibos-inspectores",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as ReciboHonorarioInspector[],
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
