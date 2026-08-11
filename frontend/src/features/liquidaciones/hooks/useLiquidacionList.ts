import { useApiQuery } from '@/hooks/callsApi/useApiQuery';
import { usePagination } from '@/hooks/system/usePagination';
import { useGenericCacheSync } from '@/hooks/cache/useGenericCacheSync';
import { useEffect } from 'react';
import type { ZodType } from 'zod';
import { paginatedResponseSchema } from '../schemas/liquidacion-base.schema';

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
  syncItem: (item: T) => void;
  removeItem: (itemId: string | number) => void;
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

  // Derive domain from queryKey (e.g., ['liquidaciones', 'edificaciones'] -> 'edificaciones')
  const domain = queryKey[1];

  const { seedDetailCaches, syncItem, removeItem } = useGenericCacheSync<T>({
    listQueryKey: queryKey,
    detailKeyFn: (item) => ['liquidaciones', domain, item.liquidacion_general.id],
  });

  const paginatedSchema = paginatedResponseSchema(schema);

  const { data, isLoading, isError, refetch } = useApiQuery({
    queryKey: [...queryKey, paginationParams.page, paginationParams.page_size],
    url: `${url}?page=${paginationParams.page}&page_size=${paginationParams.page_size}`,
    schema: paginatedSchema as ZodType<PaginatedData<T>>,
  });

  // Seed detail caches after successful query
  useEffect(() => {
    if (data?.items && data.items.length > 0) {
      seedDetailCaches(data.items);
    }
  }, [data, seedDetailCaches]);

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
    syncItem,
    removeItem,
  };
}
