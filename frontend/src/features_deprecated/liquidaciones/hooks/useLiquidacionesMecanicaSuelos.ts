/**
 * Hook para lista de liquidaciones de Mecánica de Suelos con paginación.
 * Endpoint: GET /liquidaciones/mecanica-suelos
 *
 * Versión específica para MS — sin dispatch por kind.
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { liquidacionesMecanicaSuelosResponseSchema } from "../schemas/liquidacion-mecanica-suelos.schema";
import type {
  LiquidacionesMecanicaSuelosPaginated,
  LiquidacionMecanicaSuelosListItem,
} from "../types/liquidacion-mecanica-suelos.types";

interface UseLiquidacionesMecanicaSuelosProps {
  page?: number;
  pageSize?: number;
}

export function useLiquidacionesMecanicaSuelos({
  page = 1,
  pageSize = 10,
}: UseLiquidacionesMecanicaSuelosProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> = {
    page: currentPage,
    page_size: currentPageSize,
  };

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "mecanica-suelos",
      currentPage,
      currentPageSize,
    ],
    url: "/liquidaciones/mecanica-suelos",
    schema: liquidacionesMecanicaSuelosResponseSchema,
    params,
    queryOptions: {
      select: (data): LiquidacionesMecanicaSuelosPaginated => {
        if (!data.data) {
          return {
            items: [] as LiquidacionMecanicaSuelosListItem[],
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
