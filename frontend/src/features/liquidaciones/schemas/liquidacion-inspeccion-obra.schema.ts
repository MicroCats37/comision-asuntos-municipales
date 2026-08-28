import { z } from "zod";
import {
  LiquidacionGeneralOutputSchema,
  LiquidacionTipoOutputSchema,
  paginatedResponseSchema,
} from "./liquidacion-base.schema";
import { VisitasDatosOutSchema } from "./liquidacion-visitas.schema";

// Inspeccion Obra (Visitas)
export const liquidacionInspeccionObraListItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: LiquidacionTipoOutputSchema,
  liquidacion_tipo: VisitasDatosOutSchema,
});
export const liquidacionInspeccionObraPaginatedSchema = paginatedResponseSchema(
  liquidacionInspeccionObraListItemSchema,
);
export type LiquidacionInspeccionObraListItem = z.infer<
  typeof liquidacionInspeccionObraListItemSchema
>;
