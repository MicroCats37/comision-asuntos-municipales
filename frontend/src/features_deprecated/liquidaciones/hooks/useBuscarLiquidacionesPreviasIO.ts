/**
 * Hook para buscar liquidaciones previas de Inspección de Obra por número de documento.
 * Endpoint: GET /liquidaciones/inspeccion-obra/buscar-previas
 *
 * Phase 1+: La creación de IO siempre se basa en una liquidacion_previa_id.
 * Este hook permite buscar liquidaciones previas por el documento de la entidad
 * asociada al proyecto.
 *
 * Nota: Ahora retorna LiquidacionGeneralListItemOut (EDIFICACION, HABILITACION_URBANA)
 * en lugar de liquidaciones IO previas.
 */
import { useState } from "react";
import { useApiQuery } from "@/hooks";
import { buscarLiquidacionesPreviasIOResponseSchema } from "../schemas/liquidacion-inspeccion-obra.schema";
import type {
  PaginatedLiquidacionesGenerales,
  LiquidacionGeneralListItem,
} from "../types/liquidacion-general";

interface UseBuscarLiquidacionesPreviasIOProps {
  numeroDocumento?: string;
  page?: number;
  pageSize?: number;
  enabled?: boolean;
}

export function useBuscarLiquidacionesPreviasIO({
  numeroDocumento,
  page = 1,
  pageSize = 10,
  enabled = true,
}: UseBuscarLiquidacionesPreviasIOProps = {}) {
  const [currentPage, setCurrentPage] = useState(page);
  const [currentPageSize, setCurrentPageSize] = useState(pageSize);

  const params: Record<string, string | number> | undefined = numeroDocumento
    ? {
        numero_documento: numeroDocumento,
        page: currentPage,
        page_size: currentPageSize,
      }
    : undefined;

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "inspeccion-obra",
      "buscar-previas",
      numeroDocumento ?? "all",
      currentPage,
      currentPageSize,
    ],
    url: numeroDocumento ? "/liquidaciones/inspeccion-obra/buscar-previas" : null,
    schema: buscarLiquidacionesPreviasIOResponseSchema,
    params,
    queryOptions: {
      enabled: enabled && !!numeroDocumento,
      select: (data): PaginatedLiquidacionesGenerales => {
        if (!data.data) {
          return {
            items: [] as LiquidacionGeneralListItem[],
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
    items: query.data?.items ?? ([] as LiquidacionGeneralListItem[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? currentPage,
    pageSize: query.data?.page_size ?? currentPageSize,
    totalPages: query.data?.total_pages ?? 1,
    setPage: setCurrentPage,
    setPageSize: setCurrentPageSize,
  };
}
