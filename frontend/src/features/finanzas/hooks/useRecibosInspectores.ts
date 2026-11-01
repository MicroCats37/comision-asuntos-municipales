/**
 * Hook para listar Recibos de Honorarios de Inspectores con paginación.
 * Endpoint: GET /finanzas/recibos-inspectores
 * Filtros: inspector_cip, periodo, mes
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
  inspectorCip?: string;
  periodo?: number;
  mes?: number;
  enabled?: boolean;
  /**
   * Pide el conjunto completo filtrado en una sola respuesta (sin paginación).
   * Lo usa el modal de exportación a Excel.
   */
  sinPaginacion?: boolean;
}

export function useRecibosInspectores({
  page = 1,
  pageSize = 10,
  inspectorCip,
  periodo,
  mes,
  enabled = true,
  sinPaginacion = false,
}: UseRecibosInspectoresProps = {}) {
  const params: Record<string, string | number | boolean> = {
    page,
    page_size: pageSize,
  };
  if (sinPaginacion) params.sin_paginacion = true;
  if (inspectorCip) params.inspector_cip = inspectorCip;
  if (periodo) params.periodo = periodo;
  if (mes) params.mes = mes;

  const query = useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-inspectores",
      "mensual",
      page,
      pageSize,
      inspectorCip,
      periodo,
      mes,
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
