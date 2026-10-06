/**
 * Hook para listar las ÚLTIMAS revisiones de liquidaciones GENERALES.
 * Endpoint: GET /liquidaciones/generales/ultimas-revisiones
 *
 * Soporta múltiples tipos de liquidación como parámetros repetidos:
 * ?tipo_liquidacion=EDIFICACION&tipo_liquidacion=TALUDES
 *
 * Si no se especifica ningún tipo, devuelve todos los tipos soportados.
 *
 * Agrupa por:
 * - (grupo_id, relacion_key) para liquidaciones relacionadas
 * - (proyecto_id, tipo_liquidacion) para liquidaciones no relacionadas
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

export type UltimaRevisionGeneralItem =
  | LiquidacionEdificacionesListItem
  | LiquidacionHabilitacionUrbanaListItem
  | LiquidacionMecanicaSuelosListItem
  | LiquidacionTaludesListItem
  | LiquidacionImpactoVialListItem
  | LiquidacionInspeccionObraListItem;

const ultimaRevisionGeneralItemSchema = z.union([
  liquidacionEdificacionesListItemSchema,
  liquidacionHabilitacionUrbanaListItemSchema,
  liquidacionMecanicaSuelosListItemSchema,
  liquidacionTaludesListItemSchema,
  liquidacionImpactoVialListItemSchema,
  liquidacionInspeccionObraListItemSchema,
]);

const paginatedSchema = apiResponseSchema(
  paginatedResponseSchema(ultimaRevisionGeneralItemSchema),
);

interface UseUltimaRevisionGeneralProps {
  page?: number;
  pageSize?: number;
  /** Lista de códigos de tipo_liquidacion. Si no se provee, incluye todos los tipos. */
  tipoLiquidacion?: string[];
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

export function useUltimaRevisionGeneral({
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
}: UseUltimaRevisionGeneralProps = {}) {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(pageSize));

  if (tipoLiquidacion && tipoLiquidacion.length > 0) {
    for (const tipo of tipoLiquidacion) {
      params.append("tipo_liquidacion", tipo);
    }
  }
  if (razonSocial) params.set("razon_social", razonSocial);
  if (numeroDocumento) params.set("numero_documento", numeroDocumento);
  if (numero !== undefined) params.set("numero", String(numero));
  if (expediente) params.set("expediente", expediente);
  if (direccion) params.set("direccion", direccion);
  if (nombrePropietario) params.set("nombre_propietario", nombrePropietario);

  const queryString = params.toString();

  const query = useApiQuery({
    queryKey: [
      "liquidaciones",
      "generales",
      "ultimas-revisiones",
      page,
      pageSize,
      tipoLiquidacion ? tipoLiquidacion.join(",") : "all",
      razonSocial,
      numeroDocumento,
      numero,
      expediente,
      direccion,
      nombrePropietario,
    ],
    url: `/liquidaciones/generales/ultimas-revisiones?${queryString}`,
    schema: paginatedSchema,
    queryOptions: {
      enabled,
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as UltimaRevisionGeneralItem[],
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
