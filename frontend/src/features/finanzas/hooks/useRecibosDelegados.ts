/**
 * Hook para listar Recibos de Honorarios con paginación.
 * Endpoint: GET /finanzas/recibos-delegados
 * Filtros: delegado_id, liquidacion_id
 */

import { paginatedResponseSchema } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { ReciboHonorarioDelegado } from "../schemas/recibo-honorario.schema";
import { reciboHonorarioDelegadoSchema } from "../schemas/recibo-honorario.schema";

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(reciboHonorarioDelegadoSchema),
);

interface UseRecibosDelegadosProps {
  page?: number;
  pageSize?: number;
  delegadoId?: string;
  liquidacionId?: string;
  enabled?: boolean;
}

export function useRecibosDelegados({
  page = 1,
  pageSize = 10,
  delegadoId,
  liquidacionId,
  enabled = true,
}: UseRecibosDelegadosProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (delegadoId) params.delegado_id = delegadoId;
  if (liquidacionId) params.liquidacion_id = liquidacionId;

  const query = useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-delegados",
      page,
      pageSize,
      delegadoId,
      liquidacionId,
    ],
    url: "/finanzas/recibos-delegados",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as ReciboHonorarioDelegado[],
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
