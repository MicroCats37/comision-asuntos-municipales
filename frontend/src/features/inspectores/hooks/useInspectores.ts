/**
 * Hook para lista de inspectores con paginación.
 * Usa useApiQuery genérico del proyecto.
 * Endpoint: GET /inspectores/
 */

import { useApiQuery } from "@/hooks";
import { usePagination } from "@/hooks/system/usePagination";
import {
  type InspectorOut,
  inspectoresListResponseSchema,
} from "../types/inspectores.types";

interface UseInspectoresProps {
  page?: number;
  pageSize?: number;
}

const BASE_URL = "/inspectores";

export function useInspectores(props: UseInspectoresProps = {}) {
  const { page, pageSize, onPageChange, onPageSizeChange, paginationParams } =
    usePagination({
      initialPage: props.page ?? 1,
      initialPageSize: props.pageSize ?? 10,
    });

  const query = useApiQuery({
    queryKey: ["inspectores", page, pageSize],
    url: BASE_URL,
    schema: inspectoresListResponseSchema,
    params: paginationParams,
    queryOptions: {
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as InspectorOut[],
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
    items: query.data?.items ?? ([] as InspectorOut[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: onPageChange,
    setPageSize: onPageSizeChange,
  };
}
