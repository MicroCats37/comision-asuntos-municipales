/**
 * Hook para listar las ÚLTIMAS revisiones por proyecto de Edificaciones.
 * Endpoint: GET /liquidaciones/edificaciones/ultima-revision
 * Devuelve la liquidación con mayor numero_revision por proyecto (lista paginada).
 */
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import { paginatedResponseSchema } from "../schemas/liquidacion-base.schema";
import {
  type LiquidacionEdificacionesListItem,
  liquidacionEdificacionesListItemSchema,
} from "../schemas/liquidacion-edificaciones.schema";

/** Item = LiquidacionEdificacionesListItem (3 wrappers) */
export type UltimaRevisionItem = LiquidacionEdificacionesListItem;

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(liquidacionEdificacionesListItemSchema),
);

interface UseUltimaRevisionEdificacionesProps {
  page?: number;
  pageSize?: number;
  razonSocial?: string;
  numeroDocumento?: string;
  numero?: number;
  /** Si false, la query NO se dispara (espera a que el usuario busque) */
  enabled?: boolean;
}

export function useUltimaRevisionEdificaciones({
  page = 1,
  pageSize = 10,
  razonSocial,
  numeroDocumento,
  numero,
  enabled = true,
}: UseUltimaRevisionEdificacionesProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (razonSocial) params.razon_social = razonSocial;
  if (numeroDocumento) params.numero_documento = numeroDocumento;
  if (numero !== undefined) params.numero = numero;

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "edificaciones",
      "ultima-revision",
      page,
      pageSize,
      razonSocial,
      numeroDocumento,
      numero,
    ],
    url: "/liquidaciones/edificaciones/ultima-revision",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as UltimaRevisionItem[],
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
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
    totalPages: query.data?.total_pages ?? 1,
  };
}
