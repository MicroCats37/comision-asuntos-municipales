/**
 * Hook para lista de liquidaciones con paginación.
 * Usa useApiQuery genérico del proyecto.
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { paginatedLiquidacionesResponseSchema, liquidacionSnapshotListResponseSchema } from "../schemas/liquidacion.schema";
import type { LiquidacionListItem, LiquidacionSnapshotListItem } from "../types/liquidacion-edificaciones";

interface UseLiquidacionesProps {
  page?: number;
  pageSize?: number;
}

const BASE_URL = "/liquidaciones/edificaciones";

export function useLiquidaciones({ page = 1, pageSize = 10 }: UseLiquidacionesProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params = { page: currentPage, page_size: currentPageSize };

  const query = useApiQuery({
    queryKey: ["liquidaciones", "list", currentPage, currentPageSize],
    url: BASE_URL,
    schema: paginatedLiquidacionesResponseSchema,
    params,
    queryOptions: {
      select: (data) => {
        // Extract the actual PaginatedLiquidaciones from the response wrapper
        if (!data.data) {
          return {
            items: [] as LiquidacionListItem[],
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
    items: query.data?.items ?? ([] as LiquidacionListItem[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? currentPage,
    pageSize: query.data?.page_size ?? currentPageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: setCurrentPage,
    setPageSize: setCurrentPageSize,
  };
}


/**
 * Hook para lista de snapshots de liquidaciones con paginación (cards view).
 */
interface UseLiquidacionesSnapshotsProps {
  page?: number;
  pageSize?: number;
}

export function useLiquidacionesSnapshots({ page = 1, pageSize = 10 }: UseLiquidacionesSnapshotsProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params = { page: currentPage, page_size: currentPageSize };

  const query = useApiQuery({
    queryKey: ["liquidaciones", "snapshots", currentPage, currentPageSize],
    url: `${BASE_URL}/snapshots`,
    schema: liquidacionSnapshotListResponseSchema,
    params,
    queryOptions: {
      select: (data) => {
        if (!data.data) {
          return {
            items: [] as LiquidacionSnapshotListItem[],
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
    items: query.data?.items ?? ([] as LiquidacionSnapshotListItem[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? currentPage,
    pageSize: query.data?.page_size ?? currentPageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: setCurrentPage,
    setPageSize: setCurrentPageSize,
  };
}