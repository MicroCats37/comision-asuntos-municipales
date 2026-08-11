/**
 * Hook para lista de liquidaciones de Impacto Vial con paginación.
 * Endpoint: GET /liquidaciones/impacto-vial
 *
 * Versión específica para IV — sin dispatch por kind.
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { liquidacionesImpactoVialResponseSchema } from "../schemas/liquidacion-impacto-vial.schema";
import type {
  LiquidacionesImpactoVialPaginated,
  LiquidacionImpactoVialListItem,
} from "../types/liquidacion-impacto-vial.types";

interface UseLiquidacionesImpactoVialProps {
  page?: number;
  pageSize?: number;
}

export function useLiquidacionesImpactoVial({
  page = 1,
  pageSize = 10,
}: UseLiquidacionesImpactoVialProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> = {
    page: currentPage,
    page_size: currentPageSize,
  };

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "impacto-vial",
      currentPage,
      currentPageSize,
    ],
    url: "/liquidaciones/impacto-vial",
    schema: liquidacionesImpactoVialResponseSchema,
    params,
    queryOptions: {
      select: (data): LiquidacionesImpactoVialPaginated => {
        if (!data.data) {
          return {
            items: [] as LiquidacionImpactoVialListItem[],
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
