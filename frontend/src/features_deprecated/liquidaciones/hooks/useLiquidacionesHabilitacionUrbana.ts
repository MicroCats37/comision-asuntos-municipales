/**
 * Hook para lista de liquidaciones de Habilitación Urbana con paginación.
 * Endpoint: GET /liquidaciones/habilitacion-urbana
 *
 * Versión específica para HU — sin dispatch por kind.
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { liquidacionesHabilitacionUrbanaResponseSchema } from "../schemas/liquidacion-habilitacion-urbana.schema";
import type {
  LiquidacionesHabilitacionUrbanaPaginated,
  LiquidacionHabilitacionUrbanaListItem,
} from "../types/liquidacion-habilitacion-urbana.types";

interface UseLiquidacionesHabilitacionUrbanaProps {
  page?: number;
  pageSize?: number;
}

export function useLiquidacionesHabilitacionUrbana({
  page = 1,
  pageSize = 10,
}: UseLiquidacionesHabilitacionUrbanaProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> = {
    page: currentPage,
    page_size: currentPageSize,
  };

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "habilitacion-urbana",
      currentPage,
      currentPageSize,
    ],
    url: "/liquidaciones/habilitacion-urbana",
    schema: liquidacionesHabilitacionUrbanaResponseSchema,
    params,
    queryOptions: {
      select: (data): LiquidacionesHabilitacionUrbanaPaginated => {
        if (!data.data) {
          return {
            items: [] as LiquidacionHabilitacionUrbanaListItem[],
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
