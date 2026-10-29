import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import {
  LiquidacionGeneralOutputSchema,
  LiquidacionTipoOutputSchema,
  paginatedResponseSchema,
} from "./liquidacion-base.schema";
import { PorcentajeObraDatosOutSchema } from "./liquidacion-porcentaje.schema";

// Coerce helper: backend may send Decimal as string ("123.45") or number
const num = () => z.coerce.number();

/**
 * Campos de estrategia y snapshots PO de Edificaciones.
 *
 * Espejo de `LiquidacionEdificacionesPorcentajeObraDatosOut` del backend
 * (wrapper de cálculo PO + estrategia). Se declara aparte para poder
 * reutilizarlo en el LISTADO y en el DETALLE de Edificaciones sin tocar el
 * wrapper PO compartido (`PorcentajeObraDatosOutSchema`), que siguen usando
 * Taludes, Impacto Vial, edge y legacy sin campos de estrategia.
 */
export const estrategiaCotizacionPOOutSchema = z.object({
  /** Estrategia persistida: NORMAL_SELECCIONADAS, TARIFA_HABILITADAS_PARTICIPANTES o TOTAL_EXPLICITO. */
  estrategia_cotizacion: z.string().nullish(),
  /** Snapshot de H (habilitadas del catálogo en la fecha efectiva). */
  count_habilitadas: z.number().int().nullish(),
  /** Total final autoritativo persistido (TOTAL_EXPLICITO). */
  total_explicito: num().nullish(),
  /** Snapshot del porcentaje unitario (f) de la tarifa aplicada. */
  porcentaje_tarifa: num().nullish(),
  /** Tarifa que genera el subtotal del padre. */
  tarifa_aplicada_id: z.string().nullish(),
  /** Proyección vigente de la diferencia padre - detalles (informativa). */
  acumulacion: z
    .object({
      porcentaje_acumulado: num().nullish(),
      subtotal_acumulado: num(),
    })
    .nullish(),
});

export type EstrategiaCotizacionPOOut = z.infer<
  typeof estrategiaCotizacionPOOutSchema
>;

/**
 * Wrapper de cálculo PO de Edificaciones: agrega estrategia, snapshots y
 * proyección de acumulación al wrapper PO compartido.
 *
 * Espejo de `LiquidacionEdificacionesPorcentajeObraDatosOut` del backend. Se
 * mantiene SEPARADO del wrapper PO compartido (`PorcentajeObraDatosOutSchema`)
 * para que Taludes, Impacto Vial, edge y legacy NO expongan campos de
 * estrategia PO (contrato de schemas DRY).
 */
export const edificacionesPorcentajeObraDatosOutSchema =
  PorcentajeObraDatosOutSchema.extend({
    // En TOTAL_EXPLICITO es informativo; los registros históricos pueden ser NULL.
    valor_declarado: num().nullish(),
  }).extend(estrategiaCotizacionPOOutSchema.shape);

export type EdificacionesPorcentajeObraDatosOut = z.infer<
  typeof edificacionesPorcentajeObraDatosOutSchema
>;

// Edificaciones (PorcentajeObra)
export const liquidacionEdificacionesListItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: LiquidacionTipoOutputSchema,
  liquidacion_tipo: edificacionesPorcentajeObraDatosOutSchema,
});
export const liquidacionEdificacionesPaginatedSchema = paginatedResponseSchema(
  liquidacionEdificacionesListItemSchema,
);
export type LiquidacionEdificacionesListItem = z.infer<
  typeof liquidacionEdificacionesListItemSchema
>;

/**
 * Detalle de Edificaciones (`GET /liquidaciones/edificaciones/{id}`).
 *
 * Usa el wrapper de Edificaciones (con estrategia y acumulación) en lugar del
 * wrapper PO compartido: el detalle tiene que mostrar el contexto de
 * estrategia igual que el listado. El wrapper compartido NO se toca, de modo
 * que el detalle de Taludes, Impacto Vial, edge y legacy sigue igual.
 */
export const liquidacionEdificacionesDetalleItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: LiquidacionTipoOutputSchema,
  liquidacion_tipo: edificacionesPorcentajeObraDatosOutSchema,
});
export const liquidacionEdificacionesDetalleResponseSchema =
  apiResponseSchema(liquidacionEdificacionesDetalleItemSchema);
export type LiquidacionEdificacionesDetalleItem = z.infer<
  typeof liquidacionEdificacionesDetalleItemSchema
>;
