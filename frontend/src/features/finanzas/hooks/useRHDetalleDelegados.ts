/**
 * Hook para listar filas de DetalleHonorarioDelegado (detalle flat, sin agrupar por mes).
 * Endpoint: GET /finanzas/recibos-delegados/detalle
 * Filtros: delegado_id, periodo, mes, municipalidad_id, tipo_liquidacion_codigo, numero_liquidacion
 *
 * Nota: tipoLiquidacionCodigo es obligatorio para habilitar la consulta.
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
  tipoLiquidacionCodigo?: string;
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
  tipoLiquidacionCodigo,
  numeroLiquidacion,
  enabled = true,
}: UseRHDetalleDelegadosProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (delegadoCip) {
    // CIP must be exactly 6 digits: pad with leading zeros on the request only,
    // keep visual/URL state untouched.
    const cipDigits = delegadoCip.replace(/\D/g, "");
    params.delegado_cip = cipDigits.padStart(6, "0").slice(0, 6);
  } else if (delegadoId) {
    params.delegado_id = delegadoId;
  }
  if (periodo) params.periodo = periodo;
  if (mes) params.mes = mes;
  if (municipalidadId) params.municipalidad_id = municipalidadId;
  if (tipoLiquidacionCodigo)
    params.tipo_liquidacion_codigo = tipoLiquidacionCodigo;
  if (numeroLiquidacion) params.numero_liquidacion = numeroLiquidacion;

  // Query is only enabled when the required filter is present
  const isEnabled = enabled && Boolean(tipoLiquidacionCodigo);

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
      tipoLiquidacionCodigo,
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
