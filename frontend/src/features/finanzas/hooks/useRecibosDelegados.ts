/**
 * Hook para listar Recibos de Honorarios Mensuales con paginación.
 * Endpoint: GET /finanzas/recibos-delegados
 * Filtros: delegado_cip, municipalidad_id, periodo, mes
 */

import { paginatedResponseSchema } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { ReciboHonorarioDelegadoMensual } from "../schemas/recibo-honorario.schema";
import { rhDelegadoMensualListItemSchema } from "../schemas/recibo-honorario.schema";

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(rhDelegadoMensualListItemSchema),
);

interface UseRecibosDelegadosProps {
  page?: number;
  pageSize?: number;
  delegadoCip?: string;
  municipalidadId?: string;
  periodo?: number;
  mes?: number;
  enabled?: boolean;
}

export function useRecibosDelegados({
  page = 1,
  pageSize = 10,
  delegadoCip,
  municipalidadId,
  periodo,
  mes,
  enabled = true,
}: UseRecibosDelegadosProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (delegadoCip) params.delegado_cip = delegadoCip;
  if (municipalidadId) params.municipalidad_id = municipalidadId;
  if (periodo) params.periodo = periodo;
  if (mes) params.mes = mes;

  const query = useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-delegados",
      page,
      pageSize,
      delegadoCip,
      municipalidadId,
      periodo,
      mes,
    ],
    url: "/finanzas/recibos-delegados",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as ReciboHonorarioDelegadoMensual[],
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
