/**
 * Hook para lista de liquidaciones de EDIFICACIONES con paginación.
 * Usa useApiQuery genérico del proyecto.
 * Endpoint: GET /liquidaciones/edificaciones/
 *
 * NOTA: Este hook es específico para Edificaciones. Para liquidaciones
 * generales (GET /liquidaciones) usar useLiquidacionesGenerales.
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { liquidacionesEdificacionPaginatedResponseSchema } from "../schemas/liquidacion.schema";
import type { LiquidacionEdificacionesListItem } from "../types/liquidacion-edificaciones";

interface UseLiquidacionesEdificacionesProps {
  page?: number;
  pageSize?: number;
  proyectoPublicId?: string | null;
}

interface UseLiquidacionesEdificacionesPorDocumentoProps {
  numeroDocumento?: string | null;
  page?: number;
  pageSize?: number;
}

const BASE_URL = "/liquidaciones/edificaciones";

export function useLiquidacionesEdificaciones({
  page = 1,
  pageSize = 10,
  proyectoPublicId = null,
}: UseLiquidacionesEdificacionesProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> = { page: currentPage, page_size: currentPageSize };
  if (proyectoPublicId) {
    params.proyecto_public_id = proyectoPublicId;
  }

  const query = useApiQuery({
    queryKey: ["liquidaciones", "edificaciones", currentPage, currentPageSize, proyectoPublicId],
    url: BASE_URL,
    schema: liquidacionesEdificacionPaginatedResponseSchema,
    params,
    queryOptions: {
      select: (data) => {
        // Extract the actual PaginatedLiquidaciones from the response wrapper
        if (!data.data) {
          return {
            items: [] as LiquidacionEdificacionesListItem[],
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
    items: query.data?.items ?? ([] as LiquidacionEdificacionesListItem[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? currentPage,
    pageSize: query.data?.page_size ?? currentPageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: setCurrentPage,
    setPageSize: setCurrentPageSize,
  };
}

export function useLiquidacionesEdificacionesPorDocumento({
  numeroDocumento = null,
  page = 1,
  pageSize = 10,
}: UseLiquidacionesEdificacionesPorDocumentoProps = {}) {
  const documento = numeroDocumento?.trim() ?? "";
  const params: Record<string, string | number> = {
    numero_documento: documento,
    page,
    page_size: pageSize,
  };

  const query = useApiQuery({
    queryKey: ["liquidaciones", "edificaciones", "buscar-por-documento", documento, page, pageSize],
    url: `${BASE_URL}/buscar-por-documento`,
    schema: liquidacionesEdificacionPaginatedResponseSchema,
    params,
    queryOptions: {
      enabled: documento.length === 8 || documento.length === 11,
      retry: false,
      select: (data) => {
        if (!data.data) {
          return {
            items: [] as LiquidacionEdificacionesListItem[],
            total: 0,
            page,
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
    data: query.data,
    items: query.data?.items ?? ([] as LiquidacionEdificacionesListItem[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
    totalPages: query.data?.total_pages ?? 1,
  };
}
