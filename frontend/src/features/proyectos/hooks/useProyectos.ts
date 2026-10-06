/**
 * Hook para lista de proyectos con paginación.
 * Usa useApiQuery genérico del proyecto.
 *
 * Endpoint: GET /api/proyectos/?page=&page_size=
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { paginatedProyectosResponseSchema } from "../schemas/proyecto.schema";
import type { PaginatedProyectos, ProyectoListItem } from "../types/proyecto";

interface UseProyectosProps {
  page?: number;
  pageSize?: number;
}

const BASE_URL = "/proyectos";

export function useProyectos({
  page = 1,
  pageSize = 10,
}: UseProyectosProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params = { page: currentPage, page_size: currentPageSize };

  const query = useApiQuery({
    queryKey: ["proyectos", "list", currentPage, currentPageSize],
    url: BASE_URL,
    schema: paginatedProyectosResponseSchema,
    params,
    queryOptions: {
      select: (data) => {
        if (!data.data) {
          return {
            items: [] as ProyectoListItem[],
            total: 0,
            page: currentPage,
            page_size: currentPageSize,
            total_pages: 1,
          } as PaginatedProyectos;
        }
        return data.data as PaginatedProyectos;
      },
    },
  });

  return {
    ...query,
    data: query.data,
    items: query.data?.items ?? ([] as ProyectoListItem[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? currentPage,
    pageSize: query.data?.page_size ?? currentPageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: setCurrentPage,
    setPageSize: setCurrentPageSize,
  };
}
