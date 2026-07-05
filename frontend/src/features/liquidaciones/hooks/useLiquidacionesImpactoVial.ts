/**
 * Hook para lista de liquidaciones de Impacto Vial con paginación.
 * Endpoint: GET /liquidaciones/impacto-vial
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { liquidacionesNoEdificacionResponseSchema } from "../schemas/liquidacion-no-edificacion.schema";
import type {
  LiquidacionesNoEdificacionPaginated,
  LiquidacionNoEdificacionListItem,
} from "../types/liquidacion-no-edificacion.types";

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
    schema: liquidacionesNoEdificacionResponseSchema,
    params,
    queryOptions: {
      select: (data): LiquidacionesNoEdificacionPaginated => {
        if (!data.data) {
          return {
            items: [] as LiquidacionNoEdificacionListItem[],
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
