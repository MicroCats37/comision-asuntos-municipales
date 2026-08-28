/**
 * Hook para listar liquidaciones GENERALES (cualquier tipo) — para búsqueda de previa.
 * Endpoint: GET /liquidaciones/generales/
 * Devuelve PaginatedData[LiquidacionGeneralOutput] con tipo_liquidacion.
 */

import type { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import {
  LiquidacionGeneralOutputSchema,
  paginatedResponseSchema,
} from "../schemas/liquidacion-base.schema";

export const liquidacionGeneralItemSchema = LiquidacionGeneralOutputSchema;

/** Item de liquidación general — inferido del schema real del backend */
export type LiquidacionGeneralItem = z.infer<
  typeof liquidacionGeneralItemSchema
>;

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(liquidacionGeneralItemSchema),
);

interface UseLiquidacionesGeneralesProps {
  page?: number;
  pageSize?: number;
  tipo?: string;
  documento?: string;
  razonSocial?: string;
  propietario?: string;
  /** Filter by liquidacion numero (autoincremental per type, independent sequences across types) */
  numero?: number;
  enabled?: boolean;
  /** true → usa GET /ultimas-revisiones (solo la última revisión por proyecto+tipo) */
  soloUltimasRevisiones?: boolean;
}

export function useLiquidacionesGenerales({
  page = 1,
  pageSize = 10,
  tipo,
  documento,
  razonSocial,
  propietario,
  numero,
  enabled = true,
  soloUltimasRevisiones = false,
}: UseLiquidacionesGeneralesProps = {}) {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (tipo) params.tipo = tipo;
  if (documento) params.documento = documento;
  if (razonSocial) params.razon_social = razonSocial;
  if (propietario) params.propietario = propietario;
  if (numero !== undefined) params.numero = numero;

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "generales",
      soloUltimasRevisiones ? "ultimas-revisiones" : "todas",
      page,
      pageSize,
      tipo,
      documento,
      razonSocial,
      propietario,
      numero,
    ],
    url: soloUltimasRevisiones
      ? "/liquidaciones/generales/ultimas-revisiones"
      : "/liquidaciones/generales",
    schema: paginatedSchema,
    params,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as LiquidacionGeneralItem[],
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
