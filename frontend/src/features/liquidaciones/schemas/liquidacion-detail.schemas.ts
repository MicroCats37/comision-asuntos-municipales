/**
 * Schemas de DETALLE de liquidaciones.
 * Endpoints: GET /liquidaciones/{tipo}/{id}
 *
 * El backend devuelve la estructura 3-WRAPPERS (igual que el listado):
 * { liquidacion_general, liquidacion_especifica, liquidacion_tipo }
 * donde liquidacion_tipo es el detalle según el motor (PorcentajeObra/M2/Visitas).
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import {
  LiquidacionGeneralOutputSchema,
  LiquidacionTipoOutputSchema,
} from "./liquidacion-base.schema";
import { M2DatosOutSchema } from "./liquidacion-m2.schema";
import { PorcentajeObraDatosOutSchema } from "./liquidacion-porcentaje.schema";
import { VisitasDatosOutSchema } from "./liquidacion-visitas.schema";

/** Detalle común — 3 wrappers con el motor del dominio. */
export const LiquidacionDetalleItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: LiquidacionTipoOutputSchema,
  liquidacion_tipo: z.union([
    PorcentajeObraDatosOutSchema,
    M2DatosOutSchema,
    VisitasDatosOutSchema,
  ]),
});
export type LiquidacionDetalleItem = z.infer<
  typeof LiquidacionDetalleItemSchema
>;

// ── Wrappers por tipo ─────────────────────────────────────────────────────────

/** Edificaciones (PorcentajeObra) */
export const liquidacionEdificacionOutResponseSchema = apiResponseSchema(
  LiquidacionDetalleItemSchema,
);
export type LiquidacionEdificacionOut = LiquidacionDetalleItem;

/** Taludes (PorcentajeObra) */
export const liquidacionTaludesDetailResponseSchema = apiResponseSchema(
  LiquidacionDetalleItemSchema,
);

/** Mecánica de Suelos (M2) */
export const liquidacionMecanicaSuelosDetailResponseSchema = apiResponseSchema(
  LiquidacionDetalleItemSchema,
);

/** Inspección de Obra (Visitas) */
export const liquidacionInspeccionObraDetailResponseSchema = apiResponseSchema(
  LiquidacionDetalleItemSchema,
);

/** Impacto Vial (PorcentajeObra) */
export const liquidacionImpactoVialDetailResponseSchema = apiResponseSchema(
  LiquidacionDetalleItemSchema,
);

/** Habilitación Urbana (M2) */
export const liquidacionHabilitacionUrbanaDetailResponseSchema =
  apiResponseSchema(LiquidacionDetalleItemSchema);
