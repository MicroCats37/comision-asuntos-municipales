/**
 * Hook para buscar asignaciones de inspectores (LiquidacionInspector).
 * Endpoint: GET /liquidaciones/inspectores/inspectores-asignaciones
 * Filtros: cip, liquidacion_id
 */

import { paginatedResponseSchema } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { LiquidacionInspectorAsignacion } from "../schemas/inspector-asignacion.schema";
import { liquidacionInspectorAsignacionSchema } from "../schemas/inspector-asignacion.schema";

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(liquidacionInspectorAsignacionSchema),
);

interface UseInspectoresAsignacionesProps {
  page?: number;
  pageSize?: number;
  cip?: string;
  liquidacionId?: string;
  enabled?: boolean;
}

export function useInspectoresAsignaciones({
  page = 1,
  pageSize = 10,
  cip,
  liquidacionId,
  enabled = true,
}: UseInspectoresAsignacionesProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (cip) params.cip = cip;
  if (liquidacionId) params.liquidacion_id = liquidacionId;

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "inspectores-asignaciones",
      page,
      pageSize,
      cip,
      liquidacionId,
    ],
    url: "/liquidaciones/inspectores/inspectores-asignaciones",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as LiquidacionInspectorAsignacion[],
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
