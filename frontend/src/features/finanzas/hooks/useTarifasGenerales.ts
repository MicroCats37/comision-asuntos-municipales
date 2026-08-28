/**
 * Hook para tarifas GENERALES (todas, sin filtrar por tipo).
 * Endpoint: GET /liquidaciones/tarifas
 *
 * - SIN fechas: el backend devuelve SOLO las tarifas VIGENTES de todos los tipos.
 * - CON fechas (desde/hasta): devuelve el histórico por rango de todos los tipos.
 * La consulta está SIEMPRE habilitada; los params de fecha se agregan solo si existen.
 */

import { useApiQuery } from "@/hooks";
import { usePagination } from "@/hooks/system/usePagination";
import {
  paginatedTarifaHistoricaResponseSchema,
  type TarifaHistoricaPeriodo,
} from "../types/finanzas.types";

interface UseTarifasGeneralesProps {
  fechaDesde?: string;
  fechaHasta?: string;
}

export function useTarifasGenerales({
  fechaDesde,
  fechaHasta,
}: UseTarifasGeneralesProps) {
  const { page, pageSize, onPageChange, onPageSizeChange, paginationParams } =
    usePagination({
      initialPage: 1,
      initialPageSize: 10,
    });

  // Build query params
  const params: Record<string, string | number> = {
    ...paginationParams,
  };
  if (fechaDesde) {
    params.fecha_desde = fechaDesde;
  }
  if (fechaHasta) {
    params.fecha_hasta = fechaHasta;
  }

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "tarifas",
      "generales",
      paginationParams.page,
      paginationParams.page_size,
      fechaDesde,
      fechaHasta,
    ],
    url: "/liquidaciones/tarifas",
    schema: paginatedTarifaHistoricaResponseSchema,
    params,
    queryOptions: {
      enabled: true,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as TarifaHistoricaPeriodo[],
            total: 0,
            page: 1,
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
    items: query.data?.items ?? ([] as TarifaHistoricaPeriodo[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: onPageChange,
    setPageSize: onPageSizeChange,
  };
}
