/**
 * Hook para lista de liquidaciones GENERALES con paginación.
 * Usa useApiQuery genérico del proyecto.
 * Endpoint: GET /liquidaciones
 *
 * NOTA: Este hook es para liquidaciones GENERALES (Phase 4+).
 * Para liquidaciones de Edificaciones usar useLiquidaciones.
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { liquidacionGeneralListResponseSchema } from "../schemas/liquidacion-general.schema";
import type {
  LiquidacionGeneralListItem,
  PaginatedLiquidacionesGenerales,
} from "../types/liquidacion-general";

interface UseLiquidacionesGeneralesProps {
  page?: number;
  pageSize?: number;
}

const BASE_URL = "/liquidaciones";

export function useLiquidacionesGenerales({
  page = 1,
  pageSize = 10,
}: UseLiquidacionesGeneralesProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> = {
    page: currentPage,
    page_size: currentPageSize,
  };

  const query = useApiQuery({
    queryKey: ["liquidaciones", "generales", currentPage, currentPageSize],
    url: BASE_URL,
    schema: liquidacionGeneralListResponseSchema,
    params,
    queryOptions: {
      select: (data): PaginatedLiquidacionesGenerales => {
        if (!data.data) {
          return {
            items: [] as LiquidacionGeneralListItem[],
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
    items: query.data?.items ?? ([] as LiquidacionGeneralListItem[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? currentPage,
    pageSize: query.data?.page_size ?? currentPageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: setCurrentPage,
    setPageSize: setCurrentPageSize,
  };
}
