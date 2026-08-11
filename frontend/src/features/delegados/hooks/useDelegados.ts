/**
 * Hook para lista de delegados con paginación.
 * Usa useApiQuery genérico del proyecto.
 * Endpoint: GET /delegados/
 */
import { usePagination } from "@/hooks/system/usePagination";
import { useApiQuery } from "@/hooks";
import {
  delegadosListResponseSchema,
  type DelegadoOut,
} from "../types/delegados.types";

interface UseDelegadosProps {
  page?: number;
  pageSize?: number;
}

const BASE_URL = "/delegados";

export function useDelegados(props: UseDelegadosProps = {}) {
  const { page, pageSize, onPageChange, onPageSizeChange, paginationParams } = usePagination({
    initialPage: props.page ?? 1,
    initialPageSize: props.pageSize ?? 10,
  });

  const query = useApiQuery({
    queryKey: ["delegados", page, pageSize],
    url: BASE_URL,
    schema: delegadosListResponseSchema,
    params: paginationParams,
    queryOptions: {
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as DelegadoOut[],
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
    items: query.data?.items ?? ([] as DelegadoOut[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: onPageChange,
    setPageSize: onPageSizeChange,
  };
}
