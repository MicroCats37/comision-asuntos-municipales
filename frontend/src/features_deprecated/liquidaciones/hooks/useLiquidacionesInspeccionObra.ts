/**
 * Hook para lista de liquidaciones de Inspección de Obra con paginación.
 * Endpoint: GET /liquidaciones/inspeccion-obra
 *
 * Versión específica para Inspección de Obra — sin dispatch por kind.
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { liquidacionesInspeccionObraResponseSchema } from "../schemas/liquidacion-inspeccion-obra.schema";
import type {
  LiquidacionesInspeccionObraPaginated,
  LiquidacionInspeccionObraListItem,
} from "../types/liquidacion-inspeccion-obra.types";

interface UseLiquidacionesInspeccionObraProps {
  page?: number;
  pageSize?: number;
}

export function useLiquidacionesInspeccionObra({
  page = 1,
  pageSize = 10,
}: UseLiquidacionesInspeccionObraProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> = {
    page: currentPage,
    page_size: currentPageSize,
  };

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "inspeccion-obra",
      currentPage,
      currentPageSize,
    ],
    url: "/liquidaciones/inspeccion-obra",
    schema: liquidacionesInspeccionObraResponseSchema,
    params,
    queryOptions: {
      select: (data): LiquidacionesInspeccionObraPaginated => {
        if (!data.data) {
          return {
            items: [] as LiquidacionInspeccionObraListItem[],
            total: 0,
            page: currentPage,
            page_size: currentPageSize,
            total_pages: 1,
          };
        }
        return data.data;
      },
    },
  });

  return {
    ...query,
    data: query.data,
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? currentPage,
    pageSize: query.data?.page_size ?? currentPageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: setCurrentPage,
    setPageSize: setCurrentPageSize,
  };
}
