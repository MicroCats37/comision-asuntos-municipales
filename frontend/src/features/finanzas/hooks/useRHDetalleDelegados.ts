/**
 * Hook para listar filas de DetalleHonorarioDelegado (detalle flat, sin agrupar por mes).
 * Endpoint: GET /finanzas/recibos-delegados/detalle
 * Filtros: delegado_id, periodo, mes, municipalidad_id, tipo_liquidacion_id, numero_liquidacion
 *
 * Nota: periodo y tipoLiquidacionId son obligatorios para habilitar la consulta.
 */

import { paginatedResponseSchema } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { DetalleDelegadoRow } from "../schemas/recibo-honorario.schema";
import { detalleDelegadoRowSchema } from "../schemas/recibo-honorario.schema";

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(detalleDelegadoRowSchema),
);

interface UseRHDetalleDelegadosProps {
  page?: number;
  pageSize?: number;
  delegadoId?: string;
  delegadoCip?: string;
  periodo?: number;
  mes?: number;
  municipalidadId?: string;
  tipoLiquidacionId?: string;
  numeroLiquidacion?: number;
  enabled?: boolean;
}

export function useRHDetalleDelegados({
  page = 1,
  pageSize = 20,
  delegadoId,
  delegadoCip,
  periodo,
  mes,
  municipalidadId,
  tipoLiquidacionId,
  numeroLiquidacion,
  enabled = true,
}: UseRHDetalleDelegadosProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (delegadoCip) params.delegado_cip = delegadoCip;
  else if (delegadoId) params.delegado_id = delegadoId;
  if (periodo) params.periodo = periodo;
  if (mes) params.mes = mes;
  if (municipalidadId) params.municipalidad_id = municipalidadId;
  if (tipoLiquidacionId) params.tipo_liquidacion_id = tipoLiquidacionId;
  if (numeroLiquidacion) params.numero_liquidacion = numeroLiquidacion;

  // Query is only enabled when required filters are present
  const isEnabled = enabled && Boolean(periodo && tipoLiquidacionId);

  const query = useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-delegados",
      "detalle",
      page,
      pageSize,
      delegadoCip,
      delegadoId,
      periodo,
      mes,
      municipalidadId,
      tipoLiquidacionId,
      numeroLiquidacion,
    ],
    url: "/finanzas/recibos-delegados/detalle",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled: isEnabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as DetalleDelegadoRow[],
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
