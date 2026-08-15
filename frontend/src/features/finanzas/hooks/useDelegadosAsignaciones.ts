/**
 * Hook para buscar asignaciones de delegados (LiquidacionDelegado).
 * Endpoint: GET /liquidaciones/delegados-asignaciones
 * Filtros: cip, liquidacion_id
 */

import { paginatedResponseSchema } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { LiquidacionDelegado } from "../schemas/delegado-asignacion.schema";
import { liquidacionDelegadoSchema } from "../schemas/delegado-asignacion.schema";

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(liquidacionDelegadoSchema),
);

interface UseDelegadosAsignacionesProps {
  page?: number;
  pageSize?: number;
  cip?: string;
  liquidacionId?: string;
  enabled?: boolean;
}

export function useDelegadosAsignaciones({
  page = 1,
  pageSize = 10,
  cip,
  liquidacionId,
  enabled = true,
}: UseDelegadosAsignacionesProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (cip) params.cip = cip;
  if (liquidacionId) params.liquidacion_id = liquidacionId;

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "delegados-asignaciones",
      page,
      pageSize,
      cip,
      liquidacionId,
    ],
    url: "/liquidaciones/delegados-asignaciones",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as LiquidacionDelegado[],
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
