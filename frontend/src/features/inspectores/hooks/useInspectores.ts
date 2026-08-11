/**
 * Hook para lista de inspectores con paginación.
 * Usa useApiQuery genérico del proyecto.
 * Endpoint: GET /inspectores/
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import {
  inspectoresListPayloadSchema,
  type InspectorOut,
} from "../types/inspectores.types";

interface UseInspectoresProps {
  page?: number;
  pageSize?: number;
}

const BASE_URL = "/inspectores";

export function useInspectores({
  page = 1,
  pageSize = 10,
}: UseInspectoresProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> = {
    page: currentPage,
    page_size: currentPageSize,
  };

  const query = useApiQuery({
    queryKey: ["inspectores", currentPage, currentPageSize],
    url: BASE_URL,
    schema: inspectoresListPayloadSchema,
    params,
    queryOptions: {
      select: (data) => {
        if (!data) {
          return {
            items: [] as InspectorOut[],
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
    items: query.data?.items ?? ([] as InspectorOut[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? currentPage,
    pageSize: query.data?.page_size ?? currentPageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: setCurrentPage,
    setPageSize: setCurrentPageSize,
  };
}
