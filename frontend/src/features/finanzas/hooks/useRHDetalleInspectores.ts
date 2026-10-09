/**
 * Hook para listar filas de DetalleHonorarioInspector (detalle flat, sin agrupar por mes).
 * Endpoint: GET /finanzas/recibos-inspectores/detalle
 * Filtros opcionales: inspector_id, inspector_cip, periodo, mes, municipalidad_id, numero_liquidacion
 */

import { paginatedResponseSchema } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { DetalleInspectorRow } from "../schemas/recibo-honorario.schema";
import { detalleInspectorRowSchema } from "../schemas/recibo-honorario.schema";

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(detalleInspectorRowSchema),
);

interface UseRHDetalleInspectoresProps {
  page?: number;
  pageSize?: number;
  inspectorId?: string;
  inspectorCip?: string;
  periodo?: number;
  mes?: number;
  municipalidadId?: string;
  numeroLiquidacion?: number;
  enabled?: boolean;
}

export function useRHDetalleInspectores({
  page = 1,
  pageSize = 20,
  inspectorId,
  inspectorCip,
  periodo,
  mes,
  municipalidadId,
  numeroLiquidacion,
  enabled = true,
}: UseRHDetalleInspectoresProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (inspectorCip) params.inspector_cip = inspectorCip;
  else if (inspectorId) params.inspector_id = inspectorId;
  if (periodo) params.periodo = periodo;
  if (mes) params.mes = mes;
  if (municipalidadId) params.municipalidad_id = municipalidadId;
  if (numeroLiquidacion) params.numero_liquidacion = numeroLiquidacion;

  const query = useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-inspectores",
      "detalle",
      page,
      pageSize,
      inspectorCip,
      inspectorId,
      periodo,
      mes,
      municipalidadId,
      numeroLiquidacion,
    ],
    url: "/finanzas/recibos-inspectores/detalle",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as DetalleInspectorRow[],
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
