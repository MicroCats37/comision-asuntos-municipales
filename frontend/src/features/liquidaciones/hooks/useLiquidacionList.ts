import { useApiQuery } from '@/hooks/callsApi/useApiQuery';
import { usePagination } from '@/hooks/system/usePagination';
import type { ZodType } from 'zod';
import { paginatedResponseSchema } from '../schemas/liquidacion-base.schema';
import { apiResponseSchema } from '@/types/api.types';

interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface UseLiquidacionListReturn<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

export function useLiquidacionList<T>({
  queryKey,
  url,
  schema,
}: {
  queryKey: string[];
  url: string;
  schema: ZodType<T>;
}): UseLiquidacionListReturn<T> {
  const { page, pageSize, onPageChange, onPageSizeChange, paginationParams } = usePagination();

  const paginatedSchema = apiResponseSchema(paginatedResponseSchema(schema));

  const { data: apiData, isLoading, isError, refetch } = useApiQuery({
    queryKey: [...queryKey, paginationParams.page, paginationParams.page_size],
    url,
    params: paginationParams,
    schema: paginatedSchema as ZodType<{ success: boolean; data: PaginatedData<T>; error: unknown }>,
  });

  const data = apiData?.data;

  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    page,
    pageSize,
    totalPages: data?.total_pages ?? 0,
    setPage: onPageChange,
    setPageSize: onPageSizeChange,
    isLoading,
    isError,
    refetch,
  };
}
