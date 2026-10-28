/**
 * Hook para buscar liquidaciones previas en el listado paginado de cada tipo.
 * Devuelve todas las revisiones; el endpoint de creación valida si la previa
 * seleccionada puede generar una nueva revisión.
 */
import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import { paginatedResponseSchema } from "../schemas/liquidacion-base.schema";
import {
  type LiquidacionEdificacionesListItem,
  liquidacionEdificacionesListItemSchema,
} from "../schemas/liquidacion-edificaciones.schema";
import {
  type LiquidacionHabilitacionUrbanaListItem,
  liquidacionHabilitacionUrbanaListItemSchema,
} from "../schemas/liquidacion-habilitacion-urbana.schema";
import {
  type LiquidacionImpactoVialListItem,
  liquidacionImpactoVialListItemSchema,
} from "../schemas/liquidacion-impacto-vial.schema";
import {
  type LiquidacionInspeccionObraListItem,
  liquidacionInspeccionObraListItemSchema,
} from "../schemas/liquidacion-inspeccion-obra.schema";
import {
  type LiquidacionMecanicaSuelosListItem,
  liquidacionMecanicaSuelosListItemSchema,
} from "../schemas/liquidacion-mecanica-suelos.schema";
import {
  type LiquidacionTaludesListItem,
  liquidacionTaludesListItemSchema,
} from "../schemas/liquidacion-taludes.schema";

export type LiquidacionPreviaItem =
  | LiquidacionEdificacionesListItem
  | LiquidacionHabilitacionUrbanaListItem
  | LiquidacionMecanicaSuelosListItem
  | LiquidacionTaludesListItem
  | LiquidacionImpactoVialListItem
  | LiquidacionInspeccionObraListItem;

const liquidacionPreviaItemSchema = z.union([
  liquidacionEdificacionesListItemSchema,
  liquidacionHabilitacionUrbanaListItemSchema,
  liquidacionMecanicaSuelosListItemSchema,
  liquidacionTaludesListItemSchema,
  liquidacionImpactoVialListItemSchema,
  liquidacionInspeccionObraListItemSchema,
]);

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(liquidacionPreviaItemSchema),
);

const ENDPOINT_BY_TIPO: Record<string, string> = {
  EDIFICACION: "/liquidaciones/edificaciones/",
  HABILITACION_URBANA: "/liquidaciones/habilitacion-urbana/",
  MECANICA_SUELOS: "/liquidaciones/mecanica-suelos/",
  TALUDES: "/liquidaciones/taludes/",
  IMPACTO_VIAL: "/liquidaciones/impacto-vial/",
};

export function getLiquidacionesPreviasEndpoint(
  tipoLiquidacion?: string,
): string | undefined {
  return tipoLiquidacion ? ENDPOINT_BY_TIPO[tipoLiquidacion] : undefined;
}

interface UseLiquidacionesPreviasProps {
  page?: number;
  pageSize?: number;
  /** Código de tipo_liquidacion usado para resolver su endpoint específico. */
  tipoLiquidacion?: string;
  /** Si false, la query NO se dispara (espera a que el usuario busque) */
  enabled?: boolean;
  /** Filter by entidad razon_social (icontains) */
  razonSocial?: string;
  /** Filter by entidad numero documento */
  numeroDocumento?: string;
  /** Filter by liquidacion numero (exact, per type) */
  numero?: number;
  /** Filter by expediente (icontains) */
  expediente?: string;
  /** Filter by proyecto direccion (icontains) */
  direccion?: string;
  /** Filter by proyecto nombre propietario (icontains) */
  nombrePropietario?: string;
}

export function useLiquidacionesPrevias({
  page = 1,
  pageSize = 10,
  tipoLiquidacion,
  enabled = true,
  razonSocial,
  numeroDocumento,
  numero,
  expediente,
  direccion,
  nombrePropietario,
}: UseLiquidacionesPreviasProps = {}) {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(pageSize));

  if (razonSocial) params.set("razon_social", razonSocial);
  if (numeroDocumento) params.set("documento", numeroDocumento);
  if (numero !== undefined) params.set("numero", String(numero));
  if (expediente) params.set("expediente", expediente);
  if (direccion) params.set("direccion", direccion);
  if (nombrePropietario) params.set("nombre_propietario", nombrePropietario);

  const queryString = params.toString();
  const endpoint = getLiquidacionesPreviasEndpoint(tipoLiquidacion);

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "previas",
      tipoLiquidacion,
      page,
      pageSize,
      razonSocial,
      numeroDocumento,
      numero,
      expediente,
      direccion,
      nombrePropietario,
    ],
    url: `${endpoint ?? "/liquidaciones/edificaciones/"}?${queryString}`,
    schema: paginatedSchema,
    queryOptions: {
      enabled: enabled && endpoint !== undefined,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as LiquidacionPreviaItem[],
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
