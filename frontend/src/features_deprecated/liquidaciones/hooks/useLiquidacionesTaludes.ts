/**
 * Hook para lista de liquidaciones de Taludes con paginación.
 * Endpoint: GET /liquidaciones/taludes
 *
 * Versión específica para Taludes — sin dispatch por kind.
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { liquidacionesTaludesResponseSchema } from "../schemas/liquidacion-taludes.schema";
import type {
  LiquidacionesTaludesPaginated,
  LiquidacionTaludesListItem,
} from "../types/liquidacion-taludes.types";

interface UseLiquidacionesTaludesProps {
  page?: number;
  pageSize?: number;
}

export function useLiquidacionesTaludes({
  page = 1,
  pageSize = 10,
}: UseLiquidacionesTaludesProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> = {
    page: currentPage,
    page_size: currentPageSize,
  };

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "taludes",
      currentPage,
      currentPageSize,
    ],
    url: "/liquidaciones/taludes",
    schema: liquidacionesTaludesResponseSchema,
    params,
    queryOptions: {
      select: (data): LiquidacionesTaludesPaginated => {
        if (!data.data) {
          return {
            items: [] as LiquidacionTaludesListItem[],
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
