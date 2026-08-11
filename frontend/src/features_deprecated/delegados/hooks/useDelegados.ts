/**
 * Hook para lista de delegados con paginación.
 * Usa useApiQuery genérico del proyecto.
 * Endpoint: GET /delegados/
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import {
  delegadosListPayloadSchema,
  type DelegadoOut,
} from "../types/delegados.types";

interface UseDelegadosProps {
  page?: number;
  pageSize?: number;
}

const BASE_URL = "/delegados";

export function useDelegados({
  page = 1,
  pageSize = 10,
}: UseDelegadosProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> = {
    page: currentPage,
    page_size: currentPageSize,
  };

  const query = useApiQuery({
    queryKey: ["delegados", currentPage, currentPageSize],
    url: BASE_URL,
    schema: delegadosListPayloadSchema,
    params,
    queryOptions: {
      select: (data) => {
        if (!data) {
          return {
            items: [] as DelegadoOut[],
            total: 0,
            page: currentPage,
            page_size: currentPageSize,
            total_pages: 1,
          };
        }
        return data;
      },
    },
  });

  return {
    ...query,
    data: query.data,
    items: query.data?.items ?? ([] as DelegadoOut[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? currentPage,
    pageSize: query.data?.page_size ?? currentPageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: setCurrentPage,
    setPageSize: setCurrentPageSize,
  };
}
