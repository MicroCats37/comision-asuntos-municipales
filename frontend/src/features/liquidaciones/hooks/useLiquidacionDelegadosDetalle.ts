/**
 * useLiquidacionDelegadosDetalle
 *
 * LECTURA anidada de las asignaciones de UNA liquidación concreta, con su
 * detalle RH y su RH mensual enlazado (cuando existe).
 *
 * Endpoint: GET /liquidaciones/{liquidacion_id}/delegados-asignaciones
 * Query key: ["liquidaciones", "delegados-asignaciones", liquidacionId]
 *
 * Devuelve SÓLO las asignaciones de esa liquidación (el backend las filtra;
 * el frontend no pagina ni re-filtra). Cada asignación expone su propio `id`
 * (pk de `LiquidacionDelegado`), que es el objetivo estable de la edición.
 *
 * `enabled` permite que la consulta sólo ocurra mientras el modal está
 * abierto: al abrir el browse no se pide nada.
 */

import { useApiQuery } from "@/hooks";
import {
  LiquidacionDelegadoDetalleApiResponseSchema,
  type LiquidacionDelegadoDetalleResponse,
} from "../schemas/liquidacion-delegado-detalle.schema";

interface UseLiquidacionDelegadosDetalleOptions {
  /**
   * La consulta sólo se dispara mientras sea `true`.
   * Por defecto `true` (el llamador decide).
   */
  enabled?: boolean;
}

export function useLiquidacionDelegadosDetalle(
  liquidacionId: string | null | undefined,
  { enabled = true }: UseLiquidacionDelegadosDetalleOptions = {},
) {
  const query = useApiQuery({
    queryKey: ["liquidaciones", "delegados-asignaciones", liquidacionId],
    url: liquidacionId
      ? `/liquidaciones/${liquidacionId}/delegados-asignaciones`
      : null,
    schema: LiquidacionDelegadoDetalleApiResponseSchema,
    queryOptions: {
      select: (data): LiquidacionDelegadoDetalleResponse | null =>
        data.data ?? null,
      enabled: !!liquidacionId && enabled,
    },
  });

  return {
    ...query,
    /** Asignaciones de la liquidación (o `null` mientras no haya respuesta). */
    data: query.data ?? null,
  };
}
