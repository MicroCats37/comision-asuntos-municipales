/**
 * Hook para listar las ÚLTIMAS revisiones por proyecto de Edificaciones.
 * Endpoint: GET /liquidaciones/edificaciones/ultima-revision
 * Devuelve la liquidación con mayor numero_revision por proyecto (lista paginada).
 */
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import { paginatedResponseSchema, LiquidacionGeneralOutputSchema, LiquidacionTipoOutputSchema } from "../schemas/liquidacion-base.schema";
import { PorcentajeObraDatosOutSchema } from "../schemas/liquidacion-porcentaje.schema";
import { z } from "zod";

// Item = LiquidacionEdificacionesOutput (3 wrappers)
export const ultimaRevisionItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: LiquidacionTipoOutputSchema,
  liquidacion_tipo: PorcentajeObraDatosOutSchema,
});

export type UltimaRevisionItem = z.infer<typeof ultimaRevisionItemSchema>;

const paginatedSchema = apiResponseSchema(paginatedResponseSchema(ultimaRevisionItemSchema));

interface UseUltimaRevisionEdificacionesProps {
  page?: number;
  pageSize?: number;
  razonSocial?: string;
  numeroDocumento?: string;
}

export function useUltimaRevisionEdificaciones({
  page = 1,
  pageSize = 10,
  razonSocial,
  numeroDocumento,
}: UseUltimaRevisionEdificacionesProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (razonSocial) params.razon_social = razonSocial;
  if (numeroDocumento) params.numero_documento = numeroDocumento;

  const query = useApiQuery({
    queryKey: ["liquidaciones", "edificaciones", "ultima-revision", page, pageSize, razonSocial, numeroDocumento],
    url: "/liquidaciones/edificaciones/ultima-revision",
    schema: paginatedSchema,
    params,
    queryOptions: {
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
